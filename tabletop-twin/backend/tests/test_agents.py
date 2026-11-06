"""Twelve roles, one question each, and no figure the harvested text did not state.

These tests read like the firm does: a verdict is only worth anything next to the run that
avoids it. Every threshold here is taken from `priors.json` and a case is built one year or one
cent on either side of it, so an amendment that moves a ceiling moves the test with it instead of
turning a green suite into a lie. The two exceptions are deliberate: the materiality percentage
must stay absent from the corpus for the silence test to mean anything, and a fabricated prior is
injected to prove that the silence is derived rather than written.

What this file does not test: that the chain enforces anything. That is `test_a2a.py`. And that
the corpus was parsed correctly - that is `test_priors.py`, and the two layers must be allowed to
fail separately.
"""

from __future__ import annotations

import io
import json
import os
import tempfile
from pathlib import Path

import pytest

from twin.audit import agents
from twin.audit.a2a import Bus
from twin.audit.agents import (BREACH, CLEAR, HOLD, SILENT, QUESTIONS, ROLES, Case, Firm, Finding,
                               ModelWords, Priors, RuleWords, _derogation, match_service)
from twin.audit.chain import spawn_sidecar
from twin.planner.model import ModelConfig, ModelPlanner, number_tokens
from twin.store import Store

USER = "test-firm"
CORPUS_NUMBERS = (
    "rotation_initial_max_years", "rotation_tendered_max_years", "rotation_with_tender_max_years",
    "key_partner_rotation_years", "partner_cooling_off_years", "auditor_return_cooldown_years",
    "non_audit_fee_cap_percent", "fee_dependence_percent", "participation_presumed_percent",
    "aml_record_retention_years",
)


@pytest.fixture(scope="module")
def p():
    """The derived priors, under the one name the firm's own code gives them."""
    p = Priors.load()
    absent = [name for name in CORPUS_NUMBERS if p.value(name) is None]
    assert not absent, f"the corpus no longer states {absent}: re-run python -m twin.audit.calibrate"
    assert p.value("materiality_percent_of_turnover") is None, (
        "the corpus now states a materiality percentage: the silence below needs a new control")
    return p


@pytest.fixture(scope="module")
def chain():
    box = tempfile.mkdtemp(prefix="twin-agents-")
    with spawn_sidecar(journal=os.path.join(box, "firm.journal.jsonl"), wait_sec=120.0) as running:
        receipts = running.register_roles()
        assert len(receipts) == 12 and all(r.ok for r in receipts), (
            "the firm cannot speak for an agent the registry never hired")
        assert len(running.roles()["agents"]) == 12
        yield running


@pytest.fixture()
def store():
    made = Store.temporary()
    try:
        yield made
    finally:
        made.close()


def clean(p: Priors, **over) -> Case:
    """An engagement that sits exactly on each derived figure and so breaches none of them."""
    cap = p.value("non_audit_fee_cap_percent")
    floor = p.value("fee_dependence_percent")
    retention = int(p.value("aml_record_retention_years"))
    base = {
        "client": "Northgate Energy PLC", "is_pie": True,
        "audit_fee_cents": 200_000,
        "non_audit_fee_cents": int(200_000 * cap / 100.0),
        "non_audit_services": ("translating the client's handbook into French",),
        "turnover_eur": 48_000_000.0, "balance_sheet_eur": 20_000_000.0, "employees": 300.0,
        "years_auditing": int(p.value("rotation_initial_max_years")),
        "partner_years": int(p.value("key_partner_rotation_years")),
        "previously_audited": True,
        "years_since_previous": int(p.value("partner_cooling_off_years")),
        "tender_held": True,
        "firm_fee_from_client_cents": int(9_000_000 * floor / 100.0), "firm_total_fees_cents": 9_000_000,
        "kyc_checked_years_ago": retention, "file_retention_years": retention,
    }
    return Case(**{**base, **over})


def one(p: Priors, role: str, **over) -> Finding:
    return next(f for f in Firm(p).review(clean(p, **over)) if f.role == role)


def figures(finding: Finding) -> set[str]:
    """Every number this finding was allowed to speak: its own arithmetic and its own citation."""
    given = number_tokens(json.dumps(finding.numbers, sort_keys=True))
    return given | number_tokens(json.dumps(finding.cite, sort_keys=True))


# --------------------------------------------------------------------- the arithmetic

def test_the_tenure_rule_reads_three_ceilings_and_not_one(p):
    initial = int(p.value("rotation_initial_max_years"))
    tendered = int(p.value("rotation_tendered_max_years"))
    outer = int(p.value("rotation_with_tender_max_years"))
    firm = Firm(p)

    at_initial = one(p, "engagement-partner", years_auditing=initial)
    assert at_initial.verdict == CLEAR

    past_initial = one(p, "engagement-partner", years_auditing=initial + 1, tender_held=False)
    assert past_initial.verdict == BREACH and not past_initial.binding
    assert str(initial) in past_initial.sentence

    # Between the two extensions the file has to say something the case does not: which kind
    # of tender it was. That is a hold, and a hold that binds somebody.
    between = one(p, "engagement-partner", years_auditing=tendered + 1, tender_held=True)
    assert between.verdict == HOLD and between.binding
    assert between.to_role == "audit-committee-liaison"
    assert str(tendered) in between.sentence and str(outer) in between.sentence

    past_outer = one(p, "engagement-partner", years_auditing=outer + 1, tender_held=True)
    assert past_outer.verdict == BREACH
    assert float(p.cite("rotation_with_tender_max_years")["value"]) == outer

    # Control on the tiers themselves: they are three different numbers in the text, and a
    # firm that read only two of them would have called the between-case a breach.
    assert initial < tendered < outer


def test_the_partner_clock_and_the_gap_the_clients_kind_sets(p):
    rotate = int(p.value("key_partner_rotation_years"))
    partner_gap = int(p.value("partner_cooling_off_years"))
    general_gap = int(p.value("auditor_return_cooldown_years"))

    assert one(p, "rotation-tracker", partner_years=rotate).verdict == CLEAR
    late = one(p, "rotation-tracker", partner_years=rotate + 1)
    assert late.verdict == BREACH and str(rotate) in late.sentence

    returned = one(p, "rotation-tracker", previously_audited=True, years_since_previous=partner_gap - 1)
    assert returned.verdict == BREACH and returned.cite["celex"] == p.cite("partner_cooling_off_years")["celex"]
    # The sentence the Regulation uses has no "at least" in it, so the rule that found this
    # number could not have been the one that found the Directive's.
    assert returned.cite["celex"] != p.cite("auditor_return_cooldown_years")["celex"]

    settled = one(p, "rotation-tracker", previously_audited=True, years_since_previous=partner_gap)
    assert settled.verdict == CLEAR and "gap" in settled.sentence

    # A client that is not a public-interest entity is measured by the Directive's floor, which
    # is the smaller of the two - so the same run has to be read against a different article.
    elsewhere = one(p, "rotation-tracker", is_pie=False, previously_audited=True,
                    years_since_previous=general_gap - 1)
    assert elsewhere.verdict == BREACH
    assert elsewhere.cite["celex"] == p.cite("auditor_return_cooldown_years")["celex"]


def test_the_fee_cap_and_the_dependence_floor_are_the_same_arithmetic_twice(p):
    cap = p.value("non_audit_fee_cap_percent")
    allowed = int(200_000 * cap / 100.0)
    at = one(p, "non-audit-assessor", non_audit_fee_cents=allowed)
    over = one(p, "non-audit-assessor", non_audit_fee_cents=allowed + 1)
    assert (at.verdict, over.verdict) == (CLEAR, BREACH)
    assert at.binding and not over.binding, "a breach opens no agreement for a person to sign"
    assert float(over.cite["value"]) == cap

    floor = p.value("fee_dependence_percent")
    firm_total = 9_000_000
    dependent = one(p, "fraud-risk-assessor", firm_total_fees_cents=firm_total,
                    firm_fee_from_client_cents=int(firm_total * floor / 100.0) + 1)
    assert dependent.verdict == BREACH
    assert one(p, "fraud-risk-assessor", firm_total_fees_cents=firm_total,
               firm_fee_from_client_cents=int(firm_total * floor / 100.0)).verdict == CLEAR


def test_an_empty_ledger_is_not_a_zero_ratio(p):
    """A fee the file never stated is not a fee of zero, and does not bind anybody either."""
    no_fees = one(p, "non-audit-assessor", audit_fee_cents=0)
    assert no_fees.verdict == SILENT and not no_fees.binding
    no_ledger = one(p, "fraud-risk-assessor", firm_total_fees_cents=0)
    assert no_ledger.verdict == SILENT
    no_policy = one(p, "evidence-archivist", file_retention_years=0)
    assert no_policy.verdict == SILENT
    assert one(p, "evidence-archivist", file_retention_years=1).verdict == BREACH


# ------------------------------------------------------------------- the prohibition

def test_the_prohibition_is_read_out_of_the_statute_and_not_off_a_card(p):
    categories = {c["letter"]: c for c in p.services["categories"]}
    assert list(categories) == [chr(letter) for letter in range(ord("a"), ord("k") + 1)], (
        "Article 5(1) stopped walking at " + ",".join(categories))

    bookkeeping = categories["c"]["text"].rstrip("; ")
    finding = one(p, "independence-monitor", non_audit_services=(bookkeeping,))
    assert finding.verdict == BREACH and not finding.binding
    matched = finding.numbers["matches"][0]
    assert matched["point"] == "c" and matched["words_in_common"] >= 2
    assert finding.cite["point"] == "c"
    # The derogation in 5(3) names sub-points of (a) and nothing under (c), so a firm that
    # quoted a waiver here would be quoting a permission that does not exist.
    assert _derogation(p, "c") == []

    tax = one(p, "independence-monitor", non_audit_services=(categories["a"]["text"].rstrip(": "),))
    assert tax.verdict == BREACH and tax.numbers["matches"][0]["point"] == "a"
    assert "derogate" in tax.sentence, "the waiver is part of the rule, so it belongs in the line"
    assert _derogation(p, "a"), "and it has to be a waiver the text really names"

    # Control: the same category on a client the Article does not reach.
    not_pie = one(p, "independence-monitor", is_pie=False, non_audit_services=(bookkeeping,))
    assert not_pie.verdict == CLEAR and "public-interest" in not_pie.sentence


def test_a_weak_word_match_is_a_question_not_an_answer(p):
    """One word in common is how a false positive is made, so it is escalated instead of judged."""
    almost = one(p, "independence-monitor", non_audit_services=("bookkeeping of the ledgers",))
    category, score = match_service("bookkeeping of the ledgers", p)
    assert score == 1 and category["letter"] == "c"
    assert almost.verdict == HOLD and almost.binding and almost.to_role == "audit-committee-liaison"

    nothing = one(p, "independence-monitor",
                  non_audit_services=("translating the client's handbook into French",))
    assert match_service("translating the client's handbook into French", p)[1] == 0
    assert nothing.verdict == CLEAR and nothing.binding
    # A service the prohibition does not name still needs the committee's approval, so the
    # monitor's clear and the liaison's hold are the same decision seen from two desks.
    liaison = one(p, "audit-committee-liaison", non_audit_services=("tax advice",))
    assert liaison.verdict == HOLD and liaison.cite["point"] == "4"
    assert one(p, "audit-committee-liaison", is_pie=False, non_audit_services=("tax advice",)).verdict == SILENT


# ------------------------------------------------------------------------ the silences

def test_a_silent_role_is_the_corpus_being_quiet_not_the_agent_being_lazy(p):
    assert "materiality_percent_of_turnover" in p.uncalibrated()
    silent = one(p, "materiality-reviewer")
    assert silent.verdict == SILENT and not silent.binding
    assert silent.numbers["state"] == "uncalibrated"

    # Negative control: give the same agent a calibrated prior and it stops being silent and
    # starts doing arithmetic - which is the only thing it is allowed to do with a number.
    doc = json.loads(json.dumps(p.doc))
    doc["priors"]["materiality_percent_of_turnover"] = {
        "value": 5.0, "state": "calibrated", "celex": "32000R0000", "article": "9",
        "quote": "materiality of 5 per cent of turnover", "unit": "percent",
    }
    with_number = Firm(Priors(doc)).review(clean(p))
    found = next(f for f in with_number if f.role == "materiality-reviewer")
    assert found.verdict == HOLD and found.binding
    assert found.numbers["materiality_eur"] == pytest.approx(48_000_000.0 * 5.0 / 100.0)
    assert f"{found.numbers['materiality_eur']:,.0f}" in found.sentence


def test_a_finding_cannot_quote_a_number_it_was_not_given(p):
    """The prose may restate the arithmetic; it may not add to it.

    Article and CELEX figures are allowed because a citation is provenance rather than a
    calculation, and they arrive from the same dict the verdict was drawn from.
    """
    cases = [
        clean(p),
        clean(p, years_auditing=int(p.value("rotation_with_tender_max_years")) + 2,
              partner_years=int(p.value("key_partner_rotation_years")) + 4,
              previously_audited=True, years_since_previous=0, is_pie=False),
        clean(p, non_audit_services=("bookkeeping and preparing accounting records", "valuation of shares"),
              non_audit_fee_cents=199_000, parent_holding_percent=80.0),
        clean(p, audit_fee_cents=0, firm_total_fees_cents=0, file_retention_years=0,
              non_audit_services=()),
    ]
    for case in cases:
        for finding in Firm(p).review(case):
            stray = number_tokens(finding.sentence) - figures(finding)
            assert not stray, f"{finding.role} said {sorted(stray)} that its own figures do not hold"


# --------------------------------------------------------------------- the twelve desks

def test_the_roles_are_the_agents_the_chain_will_answer(p):
    roster = json.loads((Path(__file__).resolve().parents[2] / "chain" / "roster.json")
                        .read_text(encoding="utf-8"))
    assert set(ROLES) == {agent["role"] for agent in roster["agents"]}
    assert len(ROLES) == len(QUESTIONS) == 12
    assert [role for role, _ in agents.QUESTIONS] == list(ROLES)

    firm = Firm(p)
    findings = firm.review(clean(p))
    assert [f.role for f in findings] == list(ROLES)
    assert all(f.role and f.asks and f.verdict in (CLEAR, BREACH, HOLD, SILENT) for f in findings)
    assert all(f.numbers for f in findings), "a verdict with no figures cannot be checked"
    assert sum(1 for f in findings if f.verdict == SILENT) >= 1, (
        "a firm that answers every question has invented an answer for at least one")


def test_a_review_that_answers_as_the_wrong_role_is_a_bug_not_a_finding(p, monkeypatch):
    def imposter(case, priors):
        return Finding("rotation-tracker", "answered from the wrong desk", CLEAR, "seven years")

    monkeypatch.setattr(agents, "QUESTIONS", (("engagement-partner", imposter),))
    with pytest.raises(AssertionError, match="answered as rotation-tracker"):
        Firm(p).review(clean(p))


# ------------------------------------------------------------------------- the words

class Inkwell:
    """A planner that says the line it was handed, so the words layer can be watched alone."""

    def __init__(self, text: str, route: str):
        self.text, self.last_route, self.route = text, route, route
        self.facts: list = []

    def narrate(self, ask, results, context=None, on_delta=None):
        self.facts = results
        return self.text


class Answer(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def gateway(text: str):
    """An endpoint that answers in both shapes, so whichever one is tried first says it."""

    def send(request, timeout=None):
        payload = {"output": [{"type": "message", "content": [{"text": text}]}],
                   "choices": [{"message": {"content": text}}]}
        return Answer(json.dumps(payload).encode())

    return send


def test_a_model_writes_the_sentence_and_cannot_move_the_threshold(p):
    honest = Inkwell("Non-audit work is 70% of the audit fee, which is the ceiling.", "responses:muse-test")
    finding = ModelWords(honest).phrase(one(p, "non-audit-assessor"), clean(p))
    assert finding.sentence == honest.text and finding.route == "responses:muse-test"
    assert finding.verdict == CLEAR and finding.binding, "the words changed, the decision did not"
    assert json.loads(json.dumps(honest.facts[0], sort_keys=True))["cap_percent"] == (
        p.value("non_audit_fee_cap_percent"))

    # A planner that only repeats the line it was given cannot be used to prove the guard, so
    # the guard is run end to end through the real one, which checks every number in the reply
    # against the figures it was handed. The fallback has to be visible in the route: a
    # sentence that quietly stopped coming from the model is a bug report nobody reads.
    planner = ModelPlanner(ModelConfig(base_url="https://models.example/v1", api_key="not-a-key",
                                       model="muse-test"), opener=gateway("The cap is 90 per cent."))
    checked = ModelWords(planner).phrase(one(p, "non-audit-assessor"), clean(p))
    assert checked.route.startswith("rules"), checked.route
    assert "never computed" in checked.route and "90" in checked.route, checked.route
    assert "90" not in checked.sentence
    assert checked.numbers["cap_percent"] == p.value("non_audit_fee_cap_percent")

    # Control on the same path: a reply that only restates the figures it was handed is kept,
    # and kept under the model's own route.
    plain = ModelPlanner(ModelConfig(base_url="https://models.example/v1", api_key="not-a-key",
                                     model="muse-test"),
                         opener=gateway("The work sits at the 70 per cent ceiling."))
    kept = ModelWords(plain).phrase(one(p, "non-audit-assessor"), clean(p))
    assert not kept.route.startswith("rules"), kept.route
    assert kept.sentence == "The work sits at the 70 per cent ceiling."

    said_nothing = Inkwell("", "responses:muse-test")
    quiet = ModelWords(said_nothing).phrase(one(p, "materiality-reviewer"), clean(p))
    assert quiet.sentence == one(p, "materiality-reviewer").sentence
    assert quiet.route.startswith("rules"), "an empty reply is a fallback, and says so"
    assert RuleWords().phrase(one(p, "non-audit-assessor"), clean(p)).route == "rules"


def test_the_firm_with_no_key_still_decides(p, monkeypatch):
    for name in ("META_MODEL_BASE_URL", "META_MODEL_API_KEY", "LLM_API_KEY", "OPENAI_COMPAT_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    firm = Firm.from_env()
    assert isinstance(firm.words, RuleWords) and firm.words.name == "rules"
    assert firm.words.describe()["route"] == "rules"
    assert [f.route for f in firm.review(clean(p))] == ["rules"] * 12


# ------------------------------------------------------------------------ the traffic

def test_transact_opens_only_the_findings_that_bind(p, chain, store):
    bus = Bus(chain, store=store, user_id=USER, day=4)
    case = clean(p)
    summary = Firm(p).transact(case, bus)

    findings = {f["role"]: f for f in summary["findings"]}
    binding = {role for role, f in findings.items() if f["binding"]}
    assert binding, "a case with nothing to sign proves nothing about traffic"
    assert {row["role"] for row in summary["agreements"]} == binding
    assert sum(summary["counts"].values()) == 12
    assert summary["route"] == {"route": "rules",
                                "why": "no model endpoint is configured, so the firm uses its own words"}

    for row in summary["agreements"]:
        assert [step["verb"] for step in row["steps"]] == ["propose", "accept", "attest"], row["steps"]
        assert row["state"] == "Attested", row
        assert bus.chain.agreement(row["agreement"])["state"] == "Attested"

    waiting = {row["agreement"] for row in summary["waiting_on_humans"]}
    assert waiting == {row["agreement"] for row in summary["agreements"]}
    assert not [row for row in chain.agreements() if row["state"] == "Settled"], (
        "no agent of this firm holds a key that could close one of these")

    rows = store.agent_messages(USER, limit=80)
    assert len({row["delivery_id"] for row in rows}) == len(rows) == len(summary["agreements"]) * 3
    logged = [entry for entry in store.read_log(USER) if entry["kind"] == "audit_review"]
    assert logged and logged[0]["opened"] == len(binding)
    assert logged[0]["blocked"] == [role for role, f in findings.items() if f["verdict"] == BREACH]
    assert logged[0]["waiting"] == len(waiting)


def test_a_breaching_fee_freezes_every_agreement_that_carries_it(p, chain, store):
    """The rule says breach, the bytecode says the same, and the two agree on the arithmetic.

    The assessor opens nothing because its own finding is a breach. The other roles still have
    binding findings, and every one of those proposals carries the same two fee figures - so
    the contract refuses them, and the refusal is what the panels show.
    """
    bus = Bus(chain, store=store, user_id=USER, day=5)
    allowed = int(200_000 * p.value("non_audit_fee_cap_percent") / 100.0)
    summary = Firm(p).transact(clean(p, non_audit_fee_cents=allowed + 50), bus)
    findings = {f["role"]: f for f in summary["findings"]}

    assert findings["non-audit-assessor"]["verdict"] == BREACH
    assert "non-audit-assessor" not in {row["role"] for row in summary["agreements"]}
    opened = {row["agreement"] for row in summary["agreements"] if row["state"] == "Attested"}
    assert not opened, "the cap is arithmetic, so it binds every offer that quotes these fees"
    refused = [row for row in summary["agreements"] if row["state"] == "refused"]
    assert refused and all(row["steps"][0]["refused"].startswith("FeeCapBreached") for row in refused)
    assert all(len(row["steps"]) == 1 for row in refused), "a refused offer is not chased by an accept"

    mirror = store.agent_messages(USER, limit=80)
    assert mirror and {row["state"] for row in mirror} == {"refused"}
    assert {row["refusal"].split("(")[0] for row in mirror} == {"FeeCapBreached"}

    # Control: the same case one cent back inside the cap, and the traffic flows again.
    again = Bus(chain, store=store, user_id=USER, day=5)
    cleared = Firm(p).transact(clean(p, non_audit_fee_cents=allowed), again)
    assert [row["state"] for row in cleared["agreements"]] and all(
        row["state"] == "Attested" for row in cleared["agreements"])
