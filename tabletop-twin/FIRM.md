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

## Who decides, and who checks

The verdict is the model's, when a model is wired in. Each role's answer - verdict,
sentence, the article it is standing on, and the colleague it asks to act - comes back from
the endpoint, and the firm files it only if the machine can check it. The checks need no
opinion about language. Seven of them, each one a fact about text:

- the verdict is a word this firm recognises, and there is a sentence to read at all, of a
  length a card can hold;
- the answer names a passage, and that passage is one of the six that were sent to it;
- the passage resolves in the harvest under the reference and digest the answer repeated;
- the quote is inside the text that was sent, word for word - not inside the model's
  recollection of a regulation, which is the failure all of this exists to catch;
- every figure the sentence speaks is the client's own or sits inside that quote;
- the facts it says it leaned on are facts it was handed;
- the colleague it asks to act is a role of this firm, and is not itself.

For the quote check to mean anything, the law has to be addressable rather than merely
stored, so the 299 articles are indexed: each one has an id, can be searched by a question,
and is kept with the digest of its own text. That is what lets a citation be resolved and a
quote matched against the bytes instead of against anybody's memory of them. The same reason
decides what goes into the ask: none of the figures the firm derived from the harvest is in
it, neither among the facts the model is handed nor anywhere else, because an answer that
could copy the right number out of its own prompt has been checked by nothing. Each role's
question is searched on its own words too - putting the client's file into the search was
tried, and measured, and it returned the same three articles to all twelve roles.

A judgement that fails a check is not filed, and it is not quietly swapped out either. The
deterministic rule stands in - its verdict, its words, its article - and the route says that
this happened and names the check that refused. The same is said when the endpoint never
answers, and when the harvested text is not on this machine at all, in which case no request
is spent: nothing could have been checked, and a card crediting the model with a decision no
machine could have verified would be reporting a thing that cannot happen.

That is the deliberate half of the deal. A checked judgement can still disagree with the
answer the rules would have given, and no check can notice, because the checks are about
traceability and not about being right. What bounds it is what bounded it before: no agent
signs, no model moves a threshold, and a person reads the sentence.

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
many agreements are on the contract, and how many wait for a signature. It also says who wrote
what. The leading sentence carries a byline - the model, or the rule that stood in for it and
why - and the line under it counts the whole review from each finding's own route rather than
from one route for the engagement, because one ask can be refused and the next accepted. With
no model credential every byline reads "rules" and the count collapses to "the words above came
from the rules route", which is true: the whole subsystem runs with nothing paid for.

## What is not claimed

No public network. No human signature authority. No trained weights. No materiality
percentage. The corpus is a snapshot of what open EU sources served at one time on one
machine, and a figure whose harvest cannot be reproduced should be treated as wrong until it
is. The model route has never been asked of a real endpoint on this machine either: the
judgement, the seven checks and the fallbacks are exercised against a miniature gateway that
answers the way Meta's does, on a socket, with a key that is a string in a test. So every
verdict logged here, and every sentence the example card shows, came from the rules - and the
card says so, which is the only part of this that a reader has to take on trust.
