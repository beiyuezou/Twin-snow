"""The Muse route driven over a real socket by a gateway that answers like Meta's.

No credential of the user's is involved: the key here is a string in a test and the
endpoint is a process on localhost. What is being proved is the wire and the failure
semantics — the bearer header, the path, the tool catalogue, a 401 that is not asked
twice, a 429 that is answered after the wait it named, and a reply that turns out not
to be JSON.
"""

from __future__ import annotations

import json

import pytest

from fake_muse import CHAT_PATH, MODEL, FakeMuse
from twin.planner.model import MUSE, MUSE_BASE_URL, MUSE_MODEL, ModelConfig, ModelPlanner, route_details
from twin.planner.tools import REGISTRY
from twin.world.session import Session

CONTEXT = {"horizon_days": 90, "events": [], "chasable": [], "cancellable": []}

FACTS = [{"forecast": {"pinch_day": 77, "shortfall_day": None, "median_low_dollars": 255.0,
                       "dry_run_percent": 12, "runs": 2000}}]


@pytest.fixture()
def muse(monkeypatch):
    """A live gateway, plus an environment that points exactly one endpoint at it."""
    for name in ("META_MODEL_BASE_URL", "META_MODEL_API_KEY", "META_MODEL_NAME", "MODEL_API_KEY",
                 "LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL",
                 "OPENAI_COMPAT_BASE_URL", "OPENAI_COMPAT_API_KEY", "OPENAI_COMPAT_MODEL"):
        monkeypatch.delenv(name, raising=False)
    fake = FakeMuse()
    base = fake.start()
    monkeypatch.setenv("MODEL_API_KEY", "muse-key")
    monkeypatch.setenv("META_MODEL_BASE_URL", base)
    try:
        yield fake
    finally:
        fake.stop()


def stopwatch(planner: ModelPlanner) -> tuple[ModelPlanner, list]:
    """The same endpoint and the same credential provenance, but a recorder instead of a wait."""
    sleeps: list[float] = []
    return ModelPlanner(planner.config, sleeper=sleeps.append), sleeps


def test_a_key_and_the_published_defaults_are_the_whole_configuration(muse):
    planner = ModelPlanner.from_env()
    assert planner.provider == MUSE
    assert planner.config.model == MODEL
    assert planner.config.base_url == muse.url
    # Before anyone has been asked anything, the route is still an intention.
    assert planner.last_route == ""
    assert planner.route == f"muse:{MODEL}"


def test_the_wire_carries_the_bearer_key_the_path_and_the_tool_catalogue(muse):
    muse.tool("forecast", {"horizon_days": 90})
    planner = ModelPlanner.from_env()
    calls = planner.plan("will the river hold", CONTEXT)
    assert [c.tool for c in calls] == ["forecast"]
    assert calls[0].args == {"horizon_days": 90}
    assert muse.paths == [f"POST {CHAT_PATH}"]
    assert muse.headers[0]["authorization"] == "Bearer muse-key"
    assert muse.tools_asked_for == set(REGISTRY)
    assert muse.last_body["model"] == MODEL
    assert muse.last_body["tool_choice"] == "auto"
    assert planner.last_route == f"muse:{MODEL}"


def test_a_tool_the_twin_has_not_got_is_refused_before_it_runs(muse):
    muse.tool("execute_payment", {"amount_cents": 5000})
    planner = ModelPlanner.from_env()
    calls = planner.plan("just pay the studio", CONTEXT)
    # The rules answer instead, and the reason is spoken rather than hidden.
    assert calls[0].tool == "forecast"
    assert "not a tool" in planner.last_route
    assert planner.last_route.startswith("rules (")


def test_a_refused_credential_is_not_asked_twice(muse):
    muse.refuse(401, detail="Invalid API key provided")
    planner = ModelPlanner.from_env()
    calls = planner.plan("will the river hold", CONTEXT)
    assert calls[0].tool == "forecast"
    assert muse.calls == 1
    assert "401" in planner.last_route
    # It says which variable was wrong without repeating what was in it.
    assert "MODEL_API_KEY" in planner.last_route
    assert "muse-key" not in planner.last_route


def test_a_wrong_key_value_is_refused_on_the_wire(muse):
    config = ModelConfig(base_url=muse.url, api_key="the-wrong-one", model=MODEL, provider=MUSE,
                         supplied={"api_key": "META_MODEL_API_KEY"})
    planner = ModelPlanner(config)
    planner.plan("will the river hold", CONTEXT)
    assert muse.calls == 1
    assert muse.rejected == ["Bearer the-wrong-one"]
    assert "401" in planner.last_route


def test_a_rate_limit_waits_the_pause_it_asked_for_and_asks_once_more(muse):
    muse.refuse(429, detail="Too many requests", retry_after="0.75")
    muse.tool("highlight", {"target": "driest"})
    planner, sleeps = stopwatch(ModelPlanner.from_env())
    calls = planner.plan("where does it hurt most", CONTEXT)
    assert [c.tool for c in calls] == ["highlight"]
    assert sleeps == [0.75]
    assert muse.calls == 2
    assert planner.last_route == f"muse:{MODEL}"


def test_a_wait_that_would_block_the_table_is_capped(muse):
    muse.refuse(429, retry_after="3600")
    muse.tool("forecast", {})
    config = ModelConfig(base_url=muse.url, api_key="muse-key", model=MODEL, provider=MUSE,
                         max_retry_sec=0.25, supplied={"api_key": "MODEL_API_KEY"})
    planner, sleeps = stopwatch(ModelPlanner(config))
    planner.plan("will the river hold", CONTEXT)
    assert sleeps == [0.25]


def test_a_rate_limit_that_survives_the_repair_attempt_falls_back_to_rules(muse):
    muse.refuse(429, detail="Too many requests", retry_after="0", times=2)
    planner, sleeps = stopwatch(ModelPlanner.from_env())
    calls = planner.plan("will the river hold", CONTEXT)
    assert calls[0].tool == "forecast"
    assert muse.calls == 2
    assert "asked twice" in planner.last_route
    assert planner.last_route.startswith("rules (HTTP 429")


def test_an_overloaded_gateway_is_given_one_more_attempt(muse):
    muse.refuse(503, detail="gateway is overloaded")
    muse.narration("The floor is 255 dollars at day 77 across 2,000 runs.")
    planner, _ = stopwatch(ModelPlanner.from_env())
    said = planner.narrate("what now", FACTS)
    assert "255" in said
    assert muse.calls == 2
    assert planner.last_route == f"muse:{MODEL}"


def test_an_answer_that_is_not_json_never_becomes_a_number(muse):
    muse.gibberish(text="<html>502 Bad Gateway</html>")
    planner = ModelPlanner.from_env()
    calls = planner.plan("will the river hold", CONTEXT)
    assert calls[0].tool == "forecast"
    assert "not JSON" in planner.last_route
    assert "502" not in planner.last_route


def test_a_gateway_that_hangs_up_after_the_work_is_reported_as_unreachable(muse):
    muse.silence()
    planner = ModelPlanner.from_env()
    calls = planner.plan("will the river hold", CONTEXT)
    assert calls[0].tool == "forecast"
    assert muse.host in planner.last_route
    assert "did not answer" in planner.last_route


def test_a_model_name_that_does_not_exist_is_not_retried(muse):
    config = ModelConfig(base_url=muse.url, api_key="muse-key", model="muse-imagined-9", provider=MUSE,
                         supplied={"api_key": "MODEL_API_KEY", "model": "META_MODEL_NAME"})
    planner = ModelPlanner(config)
    planner.plan("will the river hold", CONTEXT)
    assert muse.calls == 1
    assert "muse-imagined-9" in planner.last_route


def test_narration_that_only_repeats_computed_numbers_is_kept(muse):
    muse.narration("The floor is 255 dollars at day 77 across 2,000 runs.")
    planner = ModelPlanner.from_env()
    said = planner.narrate("what now", FACTS)
    assert said.startswith("The floor is 255")
    assert planner.last_route == f"muse:{MODEL}"
    assert FACTS[0]["forecast"]["median_low_dollars"] == 255.0


def test_narration_that_invents_a_dollar_figure_is_rejected_on_the_wire(muse):
    muse.narration("You will need about 9,000 dollars by Friday.")
    planner = ModelPlanner.from_env()
    said = planner.narrate("what now", FACTS)
    assert "9,000" not in said and "9000" not in said
    assert "255" in said
    assert "9000" in planner.last_route
    assert planner.last_route.startswith("rules (narration fell back")


def test_a_fact_block_reaches_the_model_as_written_numbers(muse):
    muse.narration("The floor is 255 dollars at day 77 across 2,000 runs.")
    planner = ModelPlanner.from_env()
    planner.narrate("what now", FACTS)
    prompt = json.dumps(muse.last_body["messages"])
    assert "255.0" in prompt and "pinch_day" in prompt
    assert "9000" not in prompt


def test_a_model_that_chooses_the_tool_but_not_the_words_is_reported_as_both(muse):
    muse.tool("forecast", {"horizon_days": 90})
    muse.narration("You will need about 9,000 dollars by Friday.")
    answer = Session.build().ask("will the river hold")
    # Two steps, possibly two routes: recording only the last would hide that Muse
    # chose the tool, and recording only the first would claim words it never said.
    assert answer["route"] == f"muse:{MODEL}"
    assert answer["narration_route"].startswith("rules (narration fell back")
    assert "9,000" not in answer["said"] and "255" in answer["said"]
    assert answer["calls"] == ["forecast"]


# ------------------------------------------------------------------- the report

def test_the_route_is_described_without_a_single_request(muse):
    [route] = route_details()
    assert route["provider"] == MUSE
    assert route["model"] == MODEL
    assert route["host"] == muse.host
    assert route["endpoint"] == f"{muse.url}/chat/completions"
    assert route["supplied_by"] == {"api_key": "MODEL_API_KEY", "base_url": "META_MODEL_BASE_URL", "model": ""}
    assert route["assumed"] == ["model"]
    assert route["preferred"] is True
    # Saying this cost nothing: the gateway that could answer it was never called.
    assert muse.calls == 0
    assert "muse-key" not in json.dumps(route)


def test_the_generic_endpoint_is_still_offered_beside_muse(muse, monkeypatch):
    monkeypatch.setenv("LLM_BASE_URL", "https://other.example/v1")
    monkeypatch.setenv("LLM_API_KEY", "other-key")
    monkeypatch.setenv("LLM_MODEL", "some-claude")
    routes = route_details()
    assert [r["provider"] for r in routes] == [MUSE, "openai-compatible"]
    assert [r["preferred"] for r in routes] == [True, False]
    assert routes[1]["host"] == "other.example"


def test_muse_is_reachable_by_its_published_defaults_alone(monkeypatch):
    for name in ("META_MODEL_BASE_URL", "META_MODEL_API_KEY", "META_MODEL_NAME", "MODEL_API_KEY",
                 "LLM_BASE_URL", "LLM_API_KEY", "LLM_MODEL",
                 "OPENAI_COMPAT_BASE_URL", "OPENAI_COMPAT_API_KEY", "OPENAI_COMPAT_MODEL"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MODEL_API_KEY", "someone-elses-key")
    [route] = route_details()
    assert route["host"] == "api.meta.ai"
    assert route["endpoint"] == f"{MUSE_BASE_URL}/chat/completions"
    assert route["model"] == MUSE_MODEL
