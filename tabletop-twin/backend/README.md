# Tabletop Twin service

The half that knows what a dollar is. It owns the ledger, the forecast, the forks,
the spending policy, the payment state machine, and the twin's voice, and it hands
the client a description of a scene rather than a chat reply.

## Division of labour

A seeded Monte Carlo produces the percentiles, the probability that cash runs dry on
a given day, and which day hurts most. A fork engine runs the same world again under
one changed decision and reports the difference. A calibration score compares what
the twin predicted with what actually happened, and that score — not an opinion — is
what grows the garden the client draws.

A language model chooses which of those tools to call and then explains the result.
It is never handed the job of arithmetic: narration is checked against the numbers
the code actually produced, and a model that speaks a figure nobody computed is
rejected rather than displayed. When no model is configured, or the one configured
is unreachable, the same tool choices come from a rule planner and the service
reports which route it took. Nothing on the table depends on a model answering.

## Talking to Muse

Muse is Meta's Model API, and it documents its own shape: an OpenAI-compatible
endpoint at `https://api.meta.ai/v1`, a default model of `muse-spark-1.3`, a key in
`MODEL_API_KEY`. So a key is the only thing an operator has to supply for that route —
the address and the model name are Meta's published values, and `/v1/health` says
plainly which fields came from the environment and which were assumed.
`META_MODEL_API_KEY`, `META_MODEL_BASE_URL` and `META_MODEL_NAME` override any of
them. A generic OpenAI-compatible server has no published address, so it still has to
name all three of itself, and a route with no key is no route at all.

A refusal is answered with the semantics it actually has. A 401 or 403 means the
credential was rejected and asking again only spends another request, so it is never
retried. A 429 states how long to wait and gets exactly one more attempt after that
wait, capped at two seconds, because a headset is not going to sit through an hour. A
5xx is treated as transient and given the same single repair. Whatever the endpoint
says back is flattened and truncated before it reaches a route string, and the key
itself never does: a status line may name `MODEL_API_KEY`, never what is in it.

Health reports the route it intends to use as *configured*, not as proven.
`route_is_measured` stays false until something has actually been asked, because the
environment can say what would be called and nothing more — and an answer's two halves
are reported apart, since a model that chose the tool and then could not be trusted
with the phrasing is a different fact from a model that never called.

## Supervision, not trust

Spending limits, single-payment caps, rolling daily and monthly ceilings, a
recipient allowlist, and a weekly new-subscription allowance are enforced in code.
A model response cannot widen any of them, and asking to is itself a blocked action.
Three verdicts come out of the policy engine: allow, require a hold-pinch from the
human, or deny.

Payments move through a strict state machine keyed by an idempotency key, and one
state is **unknown**: the request left, the answer never came. From there a blind
retry is refused, because a second charge could duplicate the first; the machine
asks the provider what actually happened and only then moves. A payment is not
considered finished when the money is taken — it is finished when its business
effect has been observed, and until then the twin says as much in the daily
heartbeat instead of treating the job as done.

By default settlement runs against a deterministic sandbox transport that can be
told to decline a recipient or swallow a reply after charging, so the awkward states
are exercised in tests rather than discovered in production. The real transport is
opt-in and needs its credentials. Because that transport is real HTTP, it is also
tested against a gateway that actually answers on a socket: one that loses a reply
after taking the money, one that replays an idempotency key, and one that refuses a
credential before any order exists.

## Where money can actually go

Which rail reaches which country, what it charges, and how fast it settles is a
catalog, not a set of conditions in the code. Sanctions, local data rules and fee
contracts all change, so the file that holds them is editable, dated, and names the
sources it was compiled from. Three properties hold it to:

- **Availability has a direction.** A country that can send but cannot hold money is
  refused as a recipient and accepted as a payer. A rail that will not operate inside
  a country is only refused when both ends are in it.
- **An unverified map denies nothing.** A rail refuses a country only when its own
  coverage was actually checked. A guessed refusal sends someone to a different bank
  for no reason, which is worse than the provider declining the charge — and a
  decline, unlike a lying policy, is something the state machine can handle honestly.
- **Nobody converts anything.** An amount stays in the currency of the ledger it came
  from, written in that currency's own minor units, so a Japanese figure has no
  decimals and a Bahraini one has three. There is no exchange-rate source in this
  repository, so a conversion never appears as a number — a currency the rail must
  handle shows up only as part of its fee.

Geography is checked before arithmetic: a payment the chosen rail can never deliver
is refused on that ground, and the refusal names the rails that could reach it. A
rail is only selectable when this deployment actually has a transport for it, and a
world restored from the database that cannot keep the rail it saved comes back as the
sandbox with that written into its log rather than claiming a settlement path it does
not have.

Reconciliation does not need somebody standing at the table. When
`TWIN_RECONCILE_SEC` is set and a live provider is configured, a background sweep
periodically asks the provider about every attempt still sitting in **unknown**,
across every account, and writes what came back to the audit trail. It is
deliberately modest about its own success: the provider confirming that money moved
is not the same as the paid-for thing arriving, so a swept payment is never marked as
verified, and the heartbeat keeps reporting that gap.

## Whose world it is

Nobody sees anybody else's table. An account is created with an email and a
password, and every request after that carries a bearer token; without one, the
service answers 401 rather than guessing who is asking. Each account owns its own
ledger, branches, payments, ceilings and history, and a world survives a restart
because it is written to SQLite after every call that changes it.

Everything the twin did is kept as an append-only action log — the ask, the verdict,
the rule that decided it, the gesture that settled it, the reconciliation that
finished it — and a human can read it back through an audit endpoint or as a
summary in sentences. A withdrawal asked for after the money has already moved is
recorded as the attempt it was, refused or not.

## The persona

One fictional freelance illustrator, four weeks of seeded history, ninety days
ahead. A daily heartbeat narrates what changed, what is at risk, and what the twin
got right; a wind-down closes the day with the median path, the thinnest bank, an
accuracy percentage and the garden stage.

The heartbeat is written as `heartbeat.md`, and its numbered steps are the loop the
service actually runs: a step with no rule behind it is reported as unwired by the
health endpoint rather than quietly skipped. The character's voice, the things it is
forbidden to say, and the order it speaks in all live in those documents, so the
tone is editable without touching the simulation.

## Running it

```sh
python -m pip install -e ".[dev]"
python -m uvicorn twin.api.main:app --reload
python -m pytest
```

Model and settlement credentials are read from the environment by name, and no value
is kept in this repository. Muse needs only a key, since its address and default model
are Meta's published values; a generic endpoint has no published address and so must
name all three itself. `TWIN_DB_PATH` says where the worlds live (`twin.db` in the working directory by
default, which is why it is git-ignored), and `TWIN_ALLOW_ORIGINS` lists the client
origins allowed to call it.

`python -m pytest` spends nothing and reveals nothing. The credential variables are
emptied around every test, so a suite run on a machine that happens to hold a real key
never sends a request with it. The endpoints the tests do exercise — Muse and PayPal —
are gateways the tests stand up on localhost, and they answer on a socket rather than
as stubs precisely so the awkward failures can be provoked here instead of discovered
in production: a refused credential that must not be asked twice, a rate limit that
names a wait, and a reply that never arrives after the work was done.
