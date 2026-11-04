# Tabletop Twin

A miniature of one person's next ninety days of cash, standing on their real
table, that they can push around with their hands.

The twin is not a chatbot with a 3D backdrop. Its claims are geometry: how wide
the river of cash is, how high the walls of doubt are, how thick the fog over a
late invoice, how far the boat has drifted. Numbers appear only as captions that
repeat what the shape already says.

## The metaphor

- **River of cash** runs left to right along the timeline. Its width is the
  middle forecast.
- **Banks** on either side are the tenth and ninetieth percentile. The pessimistic
  wall dips below the table when the forecast says the money simply is not there.
- **Stones** are bills, sitting at their due dates. A stone under the waterline is
  a bill the forecast cannot cover.
- **Boats** are invoices that are already late, moored upstream. Fog over a boat is
  the probability of further delay; the mast records the worst lag seen.
- **Lake** is savings. Its depth is real, not symbolic.
- **Garden** is the twin's own track record. It grows only as its predictions
  resolve, and it is the reason to come back tomorrow.
- **Orb** is the twin. It looks at what it is talking about, and it points.

## The loop

Scrub ninety days by grabbing and turning the time wheel. Test a decision by
pulling a ribbon out of the river, which spawns a second, smaller world beside the
first. Test cancelling a subscription by pulling its pipe: the same second miniature
appears, and the twin says what the pipe was worth. Approve a purchase by holding a
pinch for a full second; reject it by saying so out loud on a button. Every gesture
is a request, never a mutation.

Four weeks of history are seeded so the table is alive in the first minute, with no
setup. A daily wind-down, a published accuracy score, and a garden that only the
passage of time can grow are the return hooks.

## Division of labour

Code computes every number. The forecast, the forks, the probabilities, the
payment verdicts and the accuracy score all come from deterministic simulation and
a state machine. The language model only chooses which tool to call, in what order,
and then explains the result in plain sentences. It cannot author a figure, and a
missing or slow model never blocks the table: the client degrades to "the twin is
not answering, nothing has been spent".

Every answer also says who produced it. A route of `muse:...` was answered by Meta's
Model API; a route beginning `rules (` carries the reason it was not, in the words the
failure actually gave — a refused credential, a rate limit that outlasted the one
repair it was offered, a gateway that hung up mid-sentence. The two halves of an
answer are reported separately, because a model that picks the tool and then cannot be
trusted with the phrasing is a different fact from a model that never called. Before
anything has been asked, the service names the route it is *configured* for and marks
it as not yet measured, which is the only claim the environment alone can support.

The answer arrives as it is phrased. The service speaks Meta's agentic endpoint first —
the one that can ask for several tools in a single reply and stream its words — and
asks again in the compatible shape when a gateway objects to the request rather than to
the credential. Streaming is not a licence to show half a sentence: the narration is
released one finished sentence at a time, and only after the numbers in it have been
checked against the forecast. A stream that invents a figure freezes where it is and the
table keeps the sentence the rules computed instead, so the words on the panel are always
either verified or absent. The same rule decides which model is asked at all: an entry
the provider publishes for images, segmentation or transcription is named as the wrong
tool and costs no request, while a name nobody has checked is tried rather than refused.

## Safety

Spending limits, per-recipient ceilings and approval rules are enforced in code
before any network call. Payments pass through a strict state machine keyed by an
idempotency key, and it has an explicit **unknown** state for a response that never
arrived. In `unknown` the twin is not permitted to retry blindly; it reconciles
first. Anything above the limits, or outside the allow-listed verbs, requires a
hold-pinch from the human. Denials are silent about money: no state changes.

A separate reliability check treats a settled payment as unfinished until its
business effect is seen. Until then the twin says so in the daily heartbeat — money
taken, outcome not observed — rather than marking the job done. The garden stays a
forecast score: only resolved predictions grow it.

## Who this twin can actually pay

A big share of the world cannot receive PayPal at all, and more can only send. So the
twin keeps a dated, editable catalog of which settlement route reaches which country,
what it charges, and how long it takes — and it treats that as a first-class answer
rather than an afterthought. Ask "how should I pay this?" and it quotes every route it
knows, cheapest first, and says plainly which ones cannot deliver and why.

Three rules keep that honest:

- **Geography is checked before money.** A payment the chosen route can never arrive
  is refused on that ground alone, and the refusal names the routes that could reach
  it. Somebody in a country the provider has left is told the truth instead of
  watching a charge fail at 3 a.m.
- **An unchecked map refuses nothing.** A route only blocks a country whose coverage
  was actually verified. A guessed refusal is worse than an honest decline, because a
  decline is something the payment machine can reason about and a lying policy is not.
- **Nothing is converted.** An amount stays in the currency of the ledger it came
  from and is written in that currency's own minor units. There is no exchange-rate
  source in this project, so a currency the route must handle appears only as part of
  its fee, never as a made-up number.

A route is only selectable when the deployment really has a transport for it. Two of
the catalog's routes are quoted but not wired here, and the service says so rather
than pretending. On top of that, reconciliation now runs in the background on a
timer, so a payment whose answer never arrived is chased overnight even when nobody
has the table open — and it still does not claim the paid-for thing arrived.

## Whose table this is

Anyone can open a world, and nobody has to sign up to see one. A browser carries a
device key, the service gives an unknown key a world of its own, and every account —
claimed or anonymous — owns its own ledger, payments, branches and history. What is
refused is a request that names nobody: with neither a bearer token nor a device key the
service answers 401 rather than guessing whose cash flow to draw. A device key is a
credential and is treated as one: it is stored only as a hash, and an id short enough to
guess is refused instead of trusted. A world is written down after every change, so the
same table, the same history and the same ceilings are there after a restart.

Nothing the twin did is thrown away. Each ask, verdict, rule, gesture and
reconciliation is kept as an append-only log and can be read back as entries or as a
summary in sentences — which is what a director of finance actually needs: not a
chat transcript, but who asked for what, what stopped it, and what is still open.
A withdrawal asked for after the money has already moved is recorded as the attempt
it was.

## Accessibility

Every spoken line is also a caption. Every gesture has a voice and a gaze
alternative, and the panels are reachable by ray as well as by hand — except the one
hold that moves money, which stays a hold on purpose and refuses a click. The palette is
colourblind-safe and never the only channel: probability is carried by fog density
*and* size, risk by height *and* position relative to the table. The same rule holds
on the panels. A card changes its whole surface when its state changes — band, chip
and border together — and the chip carries the word for that state, so a person who
cannot tell the amber from the red still reads "your hold" or "offline". Nothing on
a panel is a colour alone, and the decision card names the decision it is asking for
and what the money would do.

## Scope

One fictional persona, a freelance illustrator with lumpy income. One domain, cash
flow. One horizon, ninety days. No bank linking, no investment advice, no crypto,
no multiplayer, no avatars of real people.

## Running it

Two halves: a Python service that owns the simulation, policy and model adapters,
and an Immersive Web SDK client that owns the table.

```sh
# service
python -m uvicorn twin.api.main:app --reload          # from the backend directory

# client
npm install && npm run dev                            # from the web directory
```

The client reads `VITE_TWIN_API` for the service origin. The service reads names of
credentials, never values checked into this repository. Muse — Meta's Model API —
needs one of them: `MODEL_API_KEY`, Meta's own variable name, or
`META_MODEL_API_KEY`. Its address and default model are the ones Meta publishes, so a
key alone is a whole route; `META_MODEL_BASE_URL` and `META_MODEL_NAME` replace them
when a deployment has a different agreement with the same API. Any other
OpenAI-compatible server has no published address, so it needs all three of its own:
`LLM_API_KEY` with `LLM_BASE_URL` and `LLM_MODEL`. Settlement reads
`PAYPAL_CLIENT_ID`, `PAYPAL_SECRET`, `PAYPAL_ENVIRONMENT`. A credential is the one
thing that is never assumed: with no model key the service still answers, from the
rule planner, and says which route it took. With no PayPal credentials it settles
against a deterministic sandbox transport; the real transport has to be asked for
explicitly and refuses to start without its credentials. `TWIN_DB_PATH` moves the
store, `TWIN_ALLOW_ORIGINS` says which client origins may call it (its default is the
origin the immersive client's own dev server uses, because a table that cannot reach
the service draws nothing), and `TWIN_RECONCILE_SEC` — off by default — turns on the
background sweep of payments that are still waiting for an answer.

A headset has no keyboard, so the client never asks for one. The first visit generates
a device key — 32 random bytes it keeps — and carries it on every request; the service
opens a world behind a key it has not seen. Signing up is optional and late: it puts an
email and a password on the table that device already had, rather than opening a second
one beside it. To land on an account you already have, open the app once with
`?email=...&password=...`, and a browser with no world of its own joins that account
from then on.

## Verification status

The service is covered by 287 tests that run the forecast, the forks, the policy
engine, the payment state machine, the settlement catalog, the accounts, the world a
device opens for itself, the audit trail, the real PayPal transport and the Muse route —
each of the last two against a gateway that answers on a socket, so a refused credential,
a rate limit, a reply that never arrives, a stream that invents a figure mid-sentence and
a gateway that refuses one request shape are all exercised here rather than discovered in
production. Opening a world is two writes, so two first visits from one device are raced
against each other on purpose — and the race was run with the guard switched off first,
to check that there is something to guard. No test ever holds a real credential: the
environment is emptied around every one of them, and a test that wants an endpoint stands
it up itself.

That last habit is now a file of its own. Five failures with known answers — a payment
left in a state nobody owns, a rail the catalog says cannot reach a country, a narration
quoting a figure it was never given, a click offered in place of a hold, a ledger write
that never lands — each runs twice: once expecting the bad outcome with the guard
switched off, once expecting the machine to stop it. A test that only asks whether the
fix is present can pass against a fix that does nothing; one that has to produce the
failure first cannot.

The client typechecks and builds, and its scene document validates against the SDK's
own schema and component catalog, so every asset id, component and field the code names
is real. Its account paths were then run in a real browser against the dev server, from a
profile with nothing stored: the first visit opened a table of its own with no signup and
no token, every request it made answered 200 and nothing reached the console, signing up
afterwards returned the same account, so did logging in with a token, logging out left the
device on that same world, reloading came back to it, and a second browser profile was
given a different one. A pipe pulled with a pointer forked a second world, and the
streamed answer was checked the same way, against a localhost stand-in for the model
gateway rather than a paid endpoint: the caption arrived in two pieces about a second
apart and the answer the world kept was the whole verified sentence, with the route
reported as the model that produced it.

The four panels a person reads were then rebuilt and driven the same way: the caption
card, the card that asks for a decision, the panel listing money that has left the
table, and the plate above the time wheel. Each is now a layout rather than a stack of
lines — a state band, a byline that keeps route, account and day apart instead of
squeezing them into one row, one caption at a size meant to be read at arm's length, and
a two-by-two grid of asks where four buttons used to wrap over each other. Each of the
five states moves the band, the chip and the card border at once, and the chip carries
the word for the state, so amber and blue are never the only difference.

That run put a real decision through them. A payment above the approval floor was
proposed over HTTP and the client's own heartbeat surfaced it on the decision card with
the amount, the recipient, the rail, the fee and the rule that stopped it, while the
money panel showed the same row. A pointer press on the card's reject button then sent
the refusal to the service: the request answered 200, the ledger kept it as a rejection
naming who refused and why, the record left the money panel, and the caption card
changed its whole surface to say that the record now reads cancelled. Nothing reached
the console and no request failed.

Closing that card is not the same as deciding, which is why the button writes to the
ledger rather than hiding the panel: a refusal that only moves pixels leaves no trace
for the person who has to explain the payment later.

The other half of that decision was checked rather than assumed. A button was put on the
card to settle a payment with a click, and the machine refused it — the ledger kept an
approval refusal saying that the amount needs a held pinch and recording the click as
the gesture that was tried. So the button is gone and the card now says in words what
the rule is: only a hold settles, and a click can only say no. A lighter touch is not an
accessibility improvement on a payment; a different hold is, and a controller squeeze is
a hold.

That browser run is also where a defect nobody had asked for turned up. A request naming
a device in the moment between its account existing and its ledger landing was handed the
account with nothing in it, which surfaced as a request that never answered rather than as
an error anyone could read. It is now waited for, tested from both sides, and gone from
the log above. Chasing an **unknown** payment on the next heartbeat was observed the same
way on the build before this change; the client code for it is untouched, but it was not
re-driven in the run above.

The settlement-rail, currency and background-reconciliation work is covered by the
service tests and by the client typecheck and build, and the panels that report it are
now rendered by the running client as above. What a browser cannot do is the hand. The
token is picked up by a near grab, and a pointer makes nothing happen on it: pressing
and holding where the coin sits was tried in the run above and produced no request at
all, so the one-second hold, the state that only shows while a hold is settling, and
everything about how this table reads from inside a headset remain unproven on this
machine. The state machine those gestures drive is tested in the service; the gesture
itself is not.

Live immersive evidence was **not** captured on this machine: the managed XR browser
would not start alongside the browser already running here, so no claim about headset
poses, hand tracking, controller rays or framing should be read as tested. Run
`npm run dev` on a clean machine to get that evidence.
