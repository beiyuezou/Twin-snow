# The firm beside the table

A second miniature lives on the same service as the cash twin. Twelve audit roles answer
questions about European company-audit and financial-statement rules, and the table draws
what they decided. It is not a separate product: it shares the accounts, the world a
device opens for itself, the ledger, the guardrails and the eval command, and it inherits
the rule that a number nobody computed may not be spoken.

## Where its numbers come from

The firm quotes fifteen figures — how long a partner may stay on one engagement, how much
of a client's fees an audit firm may take before independence is compromised, what a
related party is, when a group is small enough to be exempt. Fourteen of them were read
out of a harvest of the law itself: 299 articles across 8 statutes, fetched from open
EU sources, with a manifest that records what each document was, how big it came back, and
which article a figure was taken from. That manifest is what makes a derived figure
different from a remembered one: the harvest can be re-run and the arithmetic repeated, and
if the two disagree, the figure is wrong in a findable way.

The fifteenth is left uncalibrated on purpose. Materiality is normally expressed as a
percentage of turnover, and nothing in that corpus states the percentage, so the firm
refuses to quote one it could only have invented. A blank that says "nobody wrote this
down" is a better answer than a plausible number.

Every threshold card carries the article it came from and a state — derived, or waiting.
The card is the unit of trust here: a figure with no provenance is not loaded, and a model
may not move one. That last claim has a guard case, and the case has its negative control.

## What a review says

Put an engagement to the firm and each of the twelve roles answers once. Every answer is a
verdict, a sentence, and the citation the sentence is standing on. There are four verdicts
and they are not a sentiment scale: **clear** means the rule was checked and the engagement
sits inside it, **hold** means the rule binds and something has to happen, **breach** means
it is already outside the rule, and **silent** means this role has no authority over this
fact — silence is an answer, not a gap in the run.

A finding *binds* only when it names the role that has to act and the verdict is clear or
hold. On the first engagement of the review corpus that comes out as nine clear, two hold,
zero breach, one silent, and four findings that bind somebody. The corpus is fourteen
engagements across seven fictional companies, and the numbers above are what the machine
returned, not what was expected of it.

## The contract

The roles do not only email each other. They are registered on a Solidity engagement
contract running on a local EVM sidecar, and their agreements are written to it: an offer,
an acceptance, the terms each side is held to. Two things follow from putting the agreement
somewhere other than in this program's memory.

The first is that the bytecode is a second authority, and it disagrees. The contract checks
the fee cap on every proposal — 70% of the audit fee, itself derived from the regulation
rather than configured — and an engagement one basis point past the cap is refused with
`FeeCapBreached(140001, 140000)`. Nothing is recorded. That refusal is not this app's
opinion about itself; it is a name that came back out of compiled contract code, and the
panel prints that name rather than a sentence about failure. It means a finding the rules
call binding can still be a refusal on the contract, and the two accounts are both true at
once, so the card shows both.

The second is that an agreement stops short of a signature. The roles can attest to each
other; they cannot sign on behalf of a human, because there is no human key in this
deployment. Agreements therefore reach **Attested** and wait, and the count of them waiting
is shown as a state the table is in rather than a step that failed.

## Agent to agent

Between the roles, messages go over the same contract bus, and a refused write is still
journalled. That distinction is the whole point of the transport: an offer that was rejected
is evidence about what the firm tried, and a transport that drops refusals silently turns
the trail into a success story. The transcript is readable end to end, and the panel can say
which agreement is waiting on a person instead of leaving an empty row where it would have
been.

## Training

"Train" means two different things here, and only one of them happened.

What happened is calibration: the thresholds were fitted against the harvested corpus by
counting what the articles actually say, which is arithmetic over text somebody else wrote,
with the article left attached to the result. What is shipped but not run is a fine-tuning
dataset built from the firm's own logged decisions, and a script that would consume it. No
weights were trained on this machine, no checkpoint exists, and nothing in the app loads
one. The dataset is an artefact you can audit before you spend anything on it, not a claim
that the model got better.

## What the table shows

One card, four states, and every figure on it copied from a response. *On contract* when the
sidecar answered, with the roles it hired. *No contract* when it did not, with the reason the
service gave — "TWIN_CHAIN_URL is not set, so this app never asks for a chain" is a state of
the deployment, not an error. *Asking* while a review is in flight. *Offline* when the twin
stopped answering, and then the card says that instead of holding its previous numbers up as
current.

The card states how many figures were derived out of how many articles, which engagement was
put to the firm, the verdict tally, the one finding that costs the most to leave out, how
many agreements are on the contract, how many wait for a signature, and which route the
words came from. With no model credential that line reads "the words above came from the
rules route", and it is true: the whole subsystem runs with nothing paid for.

## What is not claimed

No public network. No human signature authority. No trained weights. No materiality
percentage. The corpus is a snapshot of what open EU sources served at one time on one
machine, and a figure whose harvest cannot be reproduced should be treated as wrong until it
is. The rules route is what was exercised here; a model route was never given a key, so the
firm's sentences came from the same deterministic planner as everything else in this project.
