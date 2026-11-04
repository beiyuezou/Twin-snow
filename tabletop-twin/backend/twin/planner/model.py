"""Muse (Meta's Model API) and any other OpenAI-compatible endpoint.

Meta's Model API advertises drop-in compatibility with the OpenAI SDK, so one
adapter covers Muse, Claude, or any local server that speaks the same shape. Each
endpoint is configured on its own and reported under its own name: a route that
says ``muse:...`` was answered by Meta's Model API, never by whatever happened to
be in the environment.

What may be defaulted is decided by who publishes it. Meta publishes the address
``https://api.meta.ai/v1``, the model name ``muse-spark-1.3`` and the variable
``MODEL_API_KEY``, so a Muse key alone is a complete configuration and the route
still names the variable the key came from. A generic endpoint has no published
address, so base URL, key and model must all be present before it is offered. A
credential is never defaulted, never guessed, never printed: without one there is
no endpoint, the rule planner answers, and the service says so.

Failures are reported with the semantics they actually have. A 401 or 403 means the
credential was refused and asking again only wastes a request, so it is never
retried. A 429 says how long to wait and gets exactly one more attempt after that
wait. A 5xx is transient and gets the same single repair attempt. Anything the
endpoint says back is truncated before it reaches a route string, and the key itself
never does.

The guard that matters is `assert_numbers_are_given`. A model that invents a
plausible dollar figure is worse than a model that says nothing, so narration is
checked against the numbers the forecast actually produced.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from urllib.parse import urlparse

from .rules import RulePlanner
from .tools import REGISTRY, ToolCall, ToolError, parse_calls

MUSE = "muse"
GENERIC = "openai-compatible"

CHAT_PATH = "/chat/completions"

# Published by Meta, therefore safe to assume; the key below them never is.
MUSE_BASE_URL = "https://api.meta.ai/v1"
MUSE_MODEL = "muse-spark-1.3"
MUSE_KEY_VARS = ("META_MODEL_API_KEY", "MODEL_API_KEY")
MUSE_BASE_VARS = ("META_MODEL_BASE_URL",)
MUSE_MODEL_VARS = ("META_MODEL_NAME",)
GENERIC_KEY_VARS = ("LLM_API_KEY", "OPENAI_COMPAT_API_KEY")
GENERIC_BASE_VARS = ("LLM_BASE_URL", "OPENAI_COMPAT_BASE_URL")
GENERIC_MODEL_VARS = ("LLM_MODEL", "OPENAI_COMPAT_MODEL")

# A rate limit that asks for an hour is not worth blocking a table for.
MAX_RETRY_SEC = 2.0
# Long enough to diagnose a bad request, short enough to live in an audit entry.
DETAIL_LIMIT = 140


@dataclass
class ModelConfig:
    base_url: str
    api_key: str
    model: str
    provider: str = GENERIC
    timeout_sec: float = 20.0
    max_output_tokens: int = 512
    max_retry_sec: float = MAX_RETRY_SEC
    supplied: dict[str, str] = field(default_factory=dict)

    @property
    def route(self) -> str:
        return f"{self.provider}:{self.model}"

    @property
    def host(self) -> str:
        return urlparse(self.base_url).netloc or self.base_url

    @property
    def url(self) -> str:
        return f"{self.base_url}{CHAT_PATH}"

    def reply(self, body: dict, opener=urllib.request.urlopen) -> dict:
        """One HTTP call, translated into a payload or into a reason worth showing."""
        request = urllib.request.Request(
            self.url,
            data=json.dumps(body).encode(),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
        )
        try:
            with opener(request, timeout=self.timeout_sec) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            raise _refusal(error, self) from error
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise ModelUnavailable(f"{self.host} did not answer ({type(error).__name__})") from error
        try:
            return json.loads(raw)
        except json.JSONDecodeError as error:
            raise ModelUnavailable(f"{self.host} answered with something that is not JSON") from error


class ModelUnavailable(Exception):
    """Why the endpoint did not answer, worded so it can be spoken as a route."""

    def __init__(self, reason: str, *, status: int | None = None, retryable: bool = False,
                 retry_after_sec: float | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.status = status
        self.retryable = retryable
        self.retry_after_sec = retry_after_sec

    def wait_sec(self, cap: float) -> float:
        """The pause the endpoint asked for, bounded by what this table will wait."""
        wanted = cap if self.retry_after_sec is None else self.retry_after_sec
        return max(0.0, min(wanted, cap))


def _refusal(error: urllib.error.HTTPError, config: ModelConfig) -> ModelUnavailable:
    code = error.code
    detail = _snippet(_body_of(error))
    tail = f": {detail}" if detail else ""
    if code in (401, 403):
        where = config.supplied.get("api_key")
        stamp = f" (key from {where})" if where else ""
        return ModelUnavailable(f"HTTP {code} refused the credential for {config.route}{stamp}{tail}", status=code)
    if code == 429:
        return ModelUnavailable(f"HTTP 429 rate limited by {config.host}{tail}", status=code,
                                retryable=True, retry_after_sec=_retry_after(error))
    if code >= 500:
        return ModelUnavailable(f"HTTP {code} from {config.host}{tail}", status=code, retryable=True)
    return ModelUnavailable(f"HTTP {code} from {config.host}{tail}", status=code)


def _retry_after(error: urllib.error.HTTPError) -> float | None:
    raw = error.headers.get("Retry-After") if error.headers else None
    try:
        return float(str(raw).strip())
    except (TypeError, ValueError):
        return None


def _body_of(error: urllib.error.HTTPError) -> str:
    try:
        return error.read().decode("utf-8", "replace")
    except (OSError, ValueError):
        return ""


def _snippet(text: str) -> str:
    """Flatten whatever the endpoint said into one short, log-safe clause."""
    clean = " ".join(text.split())
    if len(clean) > DETAIL_LIMIT:
        clean = clean[:DETAIL_LIMIT].rstrip() + "..."
    return clean


def _first(names: tuple[str, ...]) -> tuple[str, str]:
    """The value and the name of the first of these variables that is set."""
    for name in names:
        value = os.environ.get(name)
        if value:
            return value, name
    return "", ""


def _from_names(base_vars: tuple[str, ...], key_vars: tuple[str, ...], model_vars: tuple[str, ...],
                provider: str, default_base: str = "", default_model: str = "") -> ModelConfig | None:
    base, base_var = _first(base_vars)
    key, key_var = _first(key_vars)
    model, model_var = _first(model_vars)
    # A key is the only thing that cannot be assumed into existence.
    if not key:
        return None
    base = base or default_base
    model = model or default_model
    # A generic server has no published address or model, so a key alone is not an endpoint.
    if not base or not model:
        return None
    supplied = {"api_key": key_var, "base_url": base_var, "model": model_var}
    return ModelConfig(base_url=base.rstrip("/"), api_key=key, model=model,
                       provider=provider, supplied=supplied)


def providers_from_env() -> list[ModelConfig]:
    """Every endpoint this machine is configured for, most preferred first.

    Muse wins when both are present, and the fallback to rules is reached only
    after the endpoints actually tried have failed — so a route is a report, not
    a guess.
    """
    out = [
        _from_names(MUSE_BASE_VARS, MUSE_KEY_VARS, MUSE_MODEL_VARS, MUSE,
                    default_base=MUSE_BASE_URL, default_model=MUSE_MODEL),
        _from_names(GENERIC_BASE_VARS, GENERIC_KEY_VARS, GENERIC_MODEL_VARS, GENERIC),
    ]
    return [config for config in out if config is not None]


def providers_configured() -> list[str]:
    """Names only. An endpoint is reported as configured without repeating its key."""
    return [config.provider for config in providers_from_env()]


def route_details() -> list[dict]:
    """What each configured endpoint is, derived from the environment alone.

    Nothing here opens a socket: a deployment can say which model it intends to
    speak to, and which of those words came from the operator rather than from a
    published default, without proving it at the cost of a request.
    """
    return [
        {
            "provider": config.provider,
            "model": config.model,
            "host": config.host,
            "endpoint": config.url,
            "timeout_sec": config.timeout_sec,
            "supplied_by": dict(config.supplied),
            # Fields with no variable behind them came from a published default.
            "assumed": sorted(name for name, source in config.supplied.items() if not source),
            "preferred": index == 0,
        }
        for index, config in enumerate(providers_from_env())
    ]


class NumberFabrication(Exception):
    pass


class ModelPlanner:
    """Asks a model which tool to run. Never lets it do arithmetic."""

    name = "model"

    def __init__(self, config: ModelConfig, opener=urllib.request.urlopen,
                 fallback: RulePlanner | None = None, sleeper=time.sleep) -> None:
        self.config = config
        self._opener = opener
        self._sleeper = sleeper
        self.fallback = fallback or RulePlanner()
        self.last_route = ""
        self.voice_prompt = ""
        self.attempts = 0

    @property
    def provider(self) -> str:
        return self.config.provider

    @property
    def route(self) -> str:
        """The endpoint this planner is pointed at, before anyone has asked it anything."""
        return self.config.route

    @classmethod
    def from_env(cls) -> "ModelPlanner | None":
        configs = providers_from_env()
        return cls(configs[0]) if configs else None

    def plan(self, intent: str, context: dict) -> list[ToolCall]:
        messages = [
            {"role": "system", "content": self._system_prompt(context)},
            {"role": "user", "content": intent},
        ]
        try:
            payload = self._post(
                {
                    "model": self.config.model,
                    "messages": messages,
                    "tools": [t.to_openai() for t in REGISTRY.values()],
                    "tool_choice": "auto",
                    "max_tokens": self.config.max_output_tokens,
                }
            )
            choice = payload["choices"][0]["message"]
            calls = parse_calls(choice.get("tool_calls") or [])
            if not calls:
                raise ToolError("model returned no tool call")
            self.last_route = self.config.route
            return calls
        except (ModelUnavailable, ToolError, KeyError, json.JSONDecodeError,
                urllib.error.URLError, TimeoutError, OSError) as error:
            self.last_route = f"rules ({_why(error)})"
            return self.fallback.plan(intent, context)

    def narrate(self, intent: str, results: list[dict], context: dict | None = None) -> str:
        """Phrase the outcome in the persona's voice, then verify every number."""
        context = context or {}
        facts = json.dumps(_number_surface(results), sort_keys=True)
        given = number_tokens(facts)
        voice = self.voice_prompt or context.get("voice_prompt", "")
        try:
            payload = self._post(
                {
                    "model": self.config.model,
                    "messages": [
                        {"role": "system", "content": voice + "\nOnly use numbers from the FACTS block."},
                        {"role": "user", "content": f"FACTS: {facts}\n\nSay what changed, in one or two sentences."},
                    ],
                    "max_tokens": 160,
                }
            )
            text = payload["choices"][0]["message"]["content"].strip()
            self.assert_numbers_are_given(text, given)
            self.last_route = self.config.route
            return text
        except (NumberFabrication, ModelUnavailable, ToolError, KeyError, json.JSONDecodeError,
                urllib.error.URLError, TimeoutError, OSError) as error:
            self.last_route = f"rules (narration fell back: {_why(error)})"
            return self.fallback.narrate("", results)

    def _post(self, body: dict) -> dict:
        """Ask once. If the answer is 'busy', wait the pause asked for and ask once more.

        One repair attempt, never a loop: an endpoint that is refusing a credential
        does not become honest because it was asked twice, and a rate limit that
        survives the wait is a rate limit the table should not sit through again.
        """
        self.attempts = 1
        try:
            return self.config.reply(body, self._opener)
        except ModelUnavailable as error:
            if not error.retryable:
                raise
            self._sleeper(error.wait_sec(self.config.max_retry_sec))
        self.attempts += 1
        try:
            return self.config.reply(body, self._opener)
        except ModelUnavailable as again:
            raise ModelUnavailable(f"{again.reason} (asked twice)", status=again.status) from again

    @staticmethod
    def assert_numbers_are_given(text: str, given: set[str]) -> None:
        """Every number spoken must be a number the code produced.

        There is no allowance for "structural" digits: a model that says it is
        90 percent sure on a Tuesday is stating two facts nobody computed.
        """
        invented = {n for n in number_tokens(text) if n not in given}
        if invented:
            raise NumberFabrication(f"model produced numbers that were never computed: {sorted(invented)}")

    def _system_prompt(self, context: dict) -> str:
        events = ", ".join(f"{e['id']}={e['label']}" for e in context.get("events", ())[:24])
        return (
            "You are the planner for a cash-flow twin. Choose tools; never state numbers yourself.\n"
            f"Horizon: {context.get('horizon_days', 90)} days. "
            f"Current day: {context.get('day', 0)}. "
            f"Balance: {context.get('balance_cents', 0)} cents.\n"
            f"Ledger events: {events}\n"
            "Prefer forecast, then fork if the user is weighing a change, then highlight if they should look at something."
        )


def _why(error: Exception) -> str:
    if isinstance(error, ModelUnavailable):
        return error.reason
    if isinstance(error, KeyError):
        return f"the reply had no {error.args[0]!r}" if error.args else "the reply was missing a field"
    if isinstance(error, json.JSONDecodeError):
        return "the reply was not JSON"
    return " ".join(str(error).split()) or type(error).__name__


def _number_surface(results: list[dict]) -> dict:
    """Everything the model is allowed to say, already rounded for speech."""
    surface = []
    for result in results:
        clean = {}
        for key, value in result.items():
            if isinstance(value, dict):
                clean[key] = {k: v for k, v in value.items() if isinstance(v, (int, float, str, type(None)))}
            else:
                clean[key] = value
        surface.append(clean)
    return {"results": surface}


def number_tokens(text: str) -> set[str]:
    """Every number in a string, in the forms speech and JSON agree on.

    ``255.0``, ``255`` and ``4,200`` all normalise so that a model may restate a
    computed figure without restating it exactly.
    """
    out: set[str] = set()
    for raw in re.findall(r"\d[\d,]*(?:\.\d+)?", text):
        cleaned = raw.replace(",", "")
        out.add(cleaned)
        if "." in cleaned:
            out.add(cleaned.split(".", 1)[0])
            out.add(cleaned.rstrip("0").rstrip("."))
    return out
