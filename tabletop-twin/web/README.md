# Tabletop Twin client

The AR half: a miniature of the next ninety days of one person's cash, standing on
the table in front of them, about ninety centimetres wide.

## What this client is allowed to know

Nothing about money. It asks a service for a scene description and draws it. Every
height, width, opacity and caption on the table is copied or scaled from that
payload; the client adds no arithmetic, no thresholds, and no verdicts of its own.
If the service is unreachable it says so plainly, stops offering approvals, and
spends nothing.

The three-dimensional forms are authored in code as reusable assets so that a
quantile wall, a stone, a boat or a wheel can be placed many times and scaled
independently. Their proportions come from the metaphor, not from a downloaded
model, and each one keeps its own named parts so a hand or a ray can act on the
right piece of it.

## Hands only

Turning the time wheel scrubs the horizon. Pulling a ribbon out of the river forks
a branch and spawns a second miniature. Pulling a subscription pipe and letting it
return asks whether that subscription should be cancelled. Holding a pinch for a
full second on the approval token approves; a shorter hold does nothing. Each
gesture sends a request and waits; none of them changes state on their own.

The river itself is deliberately not grabbable, and the wheel is only ever written
by the client when no hand is holding it, so a gesture and the drawing system never
fight over the same transform.

## Accessibility

Speech is mirrored as captions on a panel, so the app is complete with sound off.
Every gesture has a ray-clickable equivalent on the panels, with one deliberate
exception: settling a payment above the approval floor takes a one-second hold, and no
button on any panel does it. That is the machine's rule, not a missing control — the
payment state machine refuses an approval whose gesture is not the held pinch and writes
the refusal down — so the alternative is a different hold (a controller squeeze works)
rather than a lighter touch. Refusing has a button. Probability, risk and
growth are each carried by two channels — fog density and size, height and
position relative to the table, garden growth rather than a dial — so colour is
never the only signal, and the palette is chosen to stay separable for colourblind
viewers. The same holds on the panels: a state change moves the band, the chip and the
card border together, and the chip spells the state out, so no panel asks a person to
read a colour to know what is being asked of them.

## Running it

```sh
npm install
npm run dev
```

Set `VITE_TWIN_API` if the service is not on its default origin. `npm run typecheck`
and `npm run build` must both pass before a change is considered finished.

## Verification status

Typechecking and the production build pass. The scene document validates against the
SDK's own scene schema and against a component catalog built from the framework's
real components plus the ones this app registers, so every asset id, component name
and field authored in the scene or written at runtime is provably declared.

The four panels were then rendered by the running client in a real browser against the
dev server, from a device world with nothing stored. The caption card, the decision
card, the money panel and the plate above the wheel all drew from the client's own
redraw rather than from any test harness. A pointer press on the decision card's reject
button sent the refusal to the service, which answered 200 and kept it as a rejection
naming the reviewer and the reason; the caption card changed its whole surface to say
what the record now reads, and the money panel went back to saying nothing is
mid-flight. The same run tried to settle a payment with a click instead of a hold and
the machine refused it, so the exception described under Accessibility is measured, not
intended. Nothing reached the console and no request failed.

What a browser cannot reach is the hand. The token is picked up by a near grab, and
holding the pointer where the coin sits produced no request at all, so the one-second
pinch, the panel state that only appears while a hold is settling, and everything about
how this table reads from inside a headset remain unproven on this machine: the managed
editor never became command-ready here. Nothing in this file should be read as "tested
on a headset" until someone runs it.
