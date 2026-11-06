"""The twelve agents, and the line each of them is not allowed to cross.

Every question the firm asks of a case has one answer from one place: the sentence in the
harvested EU text that states the rule. Where the corpus states a number, the agent quotes it
and the article it came from. Where it does not - materiality is an auditing standard's
judgement, not a figure in a regulation - the agent says so and stops, because an agent that
invents a threshold is worse than one that admits it has none. Three of the twelve roles end up
telling a human that the decision is theirs, which is the correct output, not a failure.

A model decides nothing here, and that is the point of this file: every verdict below is arithmetic
on a figure the corpus was calibrated against, so the twelve answers stand with no endpoint, no key
and no network. `ModelWords` is the only place Muse reaches in, and it reaches in at the wording -
handed the figures a finding was computed from and asked for one sentence about them, with every
number in the reply checked against that list and an invented one dropped for the rule's own words.
The verdict, the threshold and the arithmetic come from the derived priors, because a route that
cannot be trusted with arithmetic cannot be trusted with a statutory limit either.

`audit.judge` is where that changes when a machine is configured for it: there the model reads the
harvested articles themselves and makes the call, and the functions below become the answer used when
a judgement cannot be verified. Both routes are honest about which one spoke, in `Finding.route`.

What the firm does with a verdict is decided by the verdict, not by enthusiasm:

* `clear`  - open the agreement, deliver the finding, and leave it waiting for the signature no
  agent can produce. Article 5(4) sends every non-audit service to the audit committee, and the
  contract sends every agreement to a human, so nothing closes here.
* `breach` - open nothing. There is no agreement to approve when the statute forbids the work.
* `hold`   - the same traffic as `clear`, with the evidence naming what a person must decide.
* `silent` - record that the corpus gives this role no lawful basis, and move on.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from twin.audit.a2a import Bus
from twin.audit.corpus import DATA_DIR, tokens

PRIORS_FILE = DATA_DIR / "priors.json"

CLEAR, BREACH, HOLD, SILENT = "clear", "breach", "hold", "silent"


@dataclass(frozen=True)
class Case:
    """One engagement, stated only in figures a client's file and the fee ledger give.

    Nothing here is a conclusion. `is_pie` is whether the client is a public-interest entity,
    which a Member State's own list decides; the firm takes it as given and says so when a rule
    turns on it.
    """

    client: str
    audit_fee_cents: int = 0
    non_audit_fee_cents: int = 0
    non_audit_services: tuple[str, ...] = ()
    is_pie: bool = False
    is_group: bool = False
    turnover_eur: float = 0.0
    balance_sheet_eur: float = 0.0
    employees: float = 0.0
    parent_holding_percent: float = 0.0
    years_auditing: int = 0
    partner_years: int = 0
    previously_audited: bool = False
    years_since_previous: int = 0
    tender_held: bool = False
    firm_fee_from_client_cents: int = 0
    firm_total_fees_cents: int = 0
    kyc_checked_years_ago: int = 0
    file_retention_years: int = 0

    def dependence_percent(self) -> float:
        """What share of the firm's fees this one client is."""
        if not self.firm_total_fees_cents:
            return 0.0
        return round(100.0 * self.firm_fee_from_client_cents / self.firm_total_fees_cents, 2)

    def non_audit_percent(self) -> float:
        if not self.audit_fee_cents:
            return 0.0
        return round(100.0 * self.non_audit_fee_cents / self.audit_fee_cents, 2)


@dataclass(frozen=True)
class Finding:
    """What one role decided, and the sentence in the law that let it decide."""

    role: str
    asks: str
    verdict: str
    sentence: str
    numbers: dict[str, Any] = field(default_factory=dict)
    cite: dict[str, str] = field(default_factory=dict)
    to_role: str = ""
    route: str = "rules"

    @property
    def binding(self) -> bool:
        """Whether this finding has to become an agreement somebody signs."""
        return bool(self.to_role) and self.verdict in (CLEAR, HOLD)

    def with_words(self, sentence: str, route: str) -> "Finding":
        return Finding(self.role, self.asks, self.verdict, sentence, self.numbers, self.cite,
                       self.to_role, route)

    def as_dict(self) -> dict[str, Any]:
        return {
            "role": self.role, "to_role": self.to_role, "asks": self.asks, "verdict": self.verdict,
            "sentence": self.sentence, "numbers": dict(self.numbers), "cite": dict(self.cite),
            "route": self.route, "binding": self.binding,
        }


class Priors:
    """The derived thresholds, each with the article it was read out of."""

    def __init__(self, doc: dict[str, Any]) -> None:
        self.doc = doc
        self.services = doc.get("non_audit_services") or {}

    @classmethod
    def load(cls, file: str | Path | None = None) -> "Priors":
        path = Path(file) if file else PRIORS_FILE
        if not path.exists():
            raise FileNotFoundError(
                f"{path} is not there yet: run `python -m twin.audit.calibrate` to derive the"
                " firm's thresholds from the harvested corpus"
            )
        return cls(json.loads(path.read_text(encoding="utf-8")))

    def prior(self, name: str) -> dict[str, Any]:
        return (self.doc.get("priors") or {}).get(name) or {}

    def value(self, name: str) -> float | None:
        """The number, or None when the corpus did not state it. Nothing in between."""
        prior = self.prior(name)
        return prior.get("value") if prior.get("state") == "calibrated" else None

    def cite(self, name: str) -> dict[str, str]:
        prior = self.prior(name)
        if not prior:
            return {}
        return {
            "celex": str(prior.get("celex", "")), "article": str(prior.get("article", "")),
            "value": str(prior.get("value")), "state": str(prior.get("state", "")),
            "quote": str(prior.get("quote", ""))[:300],
        }

    def where(self, name: str) -> str:
        cite = self.cite(name)
        return f" ({cite['celex']} art {cite['article']})" if cite.get("celex") else ""

    def band(self, name: str) -> dict[str, Any]:
        return ((self.doc.get("size_bands") or {}).get("bands") or {}).get(name) or {}

    def uncalibrated(self) -> list[str]:
        return list(self.doc.get("uncalibrated") or [])


def match_service(request: str, priors: Priors) -> tuple[dict[str, Any], int]:
    """The Article 5(1) category a requested service falls in, and how firmly it falls there.

    The score is how many of the request's own words the category's text contains. One shared
    word is a coincidence this firm is not entitled to act on, so a weak match is escalated to
    the audit committee rather than read as a prohibition - or, worse, as an absence of one.
    """
    wanted = tokens(request)
    best, score = {}, 0
    for category in priors.services.get("categories") or []:
        haystack = tokens(category.get("text", ""))
        for sub in category.get("subs") or []:
            haystack |= tokens(sub.get("text", ""))
        hit = len(wanted & haystack)
        if hit > score:
            best, score = category, hit
    return best, score


def _article(priors: Priors, point: str = "1", quote: str = "") -> dict[str, str]:
    return {"celex": priors.services.get("celex", ""), "article": priors.services.get("article", ""),
            "point": point, "quote": (quote or priors.services.get("scope") or "")[:300]}


def _derogation(priors: Priors, letter: str) -> list[str]:
    """Which sub-points of a category 5(3) lets a Member State allow anyway."""
    return ((priors.services.get("derogation") or {}).get("points") or {}).get(letter, [])


# ------------------------------------------------------------------ the twelve questions

def engagement_partner(case: Case, p: Priors) -> Finding:
    """May this firm still be the auditor? Tenure is a ceiling in the Regulation, not a habit.

    Three ceilings come out of Article 17, not one: the initial term, the term a tender buys, and
    the outer bound only a tender involving more than one firm reaches. Between the second and the
    third the file has to say something this firm is not given, so the verdict there is a hold.
    """
    asks = "may this firm continue to audit this client"
    initial = p.value("rotation_initial_max_years")
    tendered = p.value("rotation_tendered_max_years")
    outer = p.value("rotation_with_tender_max_years")
    cite = p.cite("rotation_initial_max_years")
    numbers = {"years_auditing": case.years_auditing, "initial_max_years": initial,
               "tendered_max_years": tendered, "outer_max_years": outer,
               "tender_held": case.tender_held, "is_public_interest_entity": case.is_pie}
    if initial is None or tendered is None or outer is None:
        return Finding("engagement-partner", asks, SILENT,
                       "The corpus states no complete set of rotation ceilings, so this firm has no "
                       "lawful tenure rule to apply.", numbers, cite)
    if case.years_auditing > outer:
        return Finding("engagement-partner", asks, BREACH,
                       f"{case.years_auditing} years on this client is past the {outer:g}-year bound that "
                       f"even the widest tender reaches{p.where('rotation_with_tender_max_years')}.",
                       numbers, p.cite("rotation_with_tender_max_years"))
    if case.years_auditing > initial and not case.tender_held:
        return Finding("engagement-partner", asks, BREACH,
                       f"{case.years_auditing} years past the initial {initial:g}-year term with no tender"
                       f" held{p.where('rotation_initial_max_years')}.", numbers, cite)
    if case.years_auditing > tendered:
        return Finding("engagement-partner", asks, HOLD,
                       f"{case.years_auditing} years is past the {tendered:g}-year tier a tender buys and "
                       f"inside the {outer:g}-year bound, which the text reserves for a tender that "
                       f"involved more than one firm or early tendering - a fact about this engagement the "
                       f"file does not state{p.where('rotation_tendered_max_years')}.",
                       numbers, p.cite("rotation_tendered_max_years"), "audit-committee-liaison")
    return Finding("engagement-partner", asks, CLEAR,
                   f"{case.years_auditing} of at most {tendered:g} years on a tender, "
                   f"{initial:g} without one"
                   f"{p.where('rotation_initial_max_years')}.", numbers, cite, "rotation-tracker")


def rotation_tracker(case: Case, p: Priors) -> Finding:
    """The signing partner's own clock, and the gap required before returning to an old client.

    Two different sentences state the gap. The Regulation gives the partner of a public-interest
    entity three years; the Directive gives any other auditor one, and a Member State may not go
    below it. Which one applies is a fact about the client, so the agent asks for that fact before
    it asks for a number.
    """
    asks = "is the signing partner still eligible"
    partner = p.value("key_partner_rotation_years")
    name = "partner_cooling_off_years" if case.is_pie else "auditor_return_cooldown_years"
    cooling = p.value(name)
    cite = p.cite("key_partner_rotation_years")
    numbers = {"partner_years": case.partner_years, "rotate_after_years": partner,
               "years_since_previous_audit": case.years_since_previous,
               "previously_audited": case.previously_audited, "cooling_off_years": cooling,
               "cooling_off_rule": name, "is_public_interest_entity": case.is_pie}
    if partner is None:
        return Finding("rotation-tracker", asks, SILENT,
                       "No rotation period for a key audit partner was derived from the corpus.",
                       numbers, cite)
    if case.partner_years > partner:
        return Finding("rotation-tracker", asks, BREACH,
                       f"The signing partner has held this client for {case.partner_years} years, past the"
                       f" {partner:g}-year limit{p.where('key_partner_rotation_years')}.", numbers, cite)
    cool = p.cite(name)
    if case.previously_audited and cooling is not None and case.years_since_previous < cooling:
        return Finding("rotation-tracker", asks, BREACH,
                       f"Back on the engagement after {case.years_since_previous} year(s) where this "
                       f"client's kind requires at least {cooling:g}{p.where(name)}.", numbers, cool)
    gap = (f", and the {cooling:g}-year gap after its previous audit is complete"
           if case.previously_audited and cooling is not None
           and case.years_since_previous >= cooling else "")
    return Finding("rotation-tracker", asks, CLEAR,
                   f"{case.partner_years} of {partner:g} years for the signing partner"
                   f"{p.where('key_partner_rotation_years')}{gap}.", numbers, cite)


def independence_monitor(case: Case, p: Priors) -> Finding:
    """The Article 5(1) list, read out of the statute rather than from a list typed in here."""
    asks = "do the requested non-audit services breach the prohibition"
    cite = _article(p)
    numbers: dict[str, Any] = {"requested": list(case.non_audit_services),
                               "is_public_interest_entity": case.is_pie}
    if not case.non_audit_services:
        return Finding("independence-monitor", asks, CLEAR,
                       "The client has asked for no non-audit service, so there is nothing to prohibit.",
                       numbers, cite)
    if not case.is_pie:
        return Finding("independence-monitor", asks, CLEAR,
                       f"Article 5(1) binds the audit of a public-interest entity and {case.client} is not"
                       f" one, so this firm does not apply the prohibition to it.", numbers, cite)
    breaches, weak = [], []
    for request in case.non_audit_services:
        category, score = match_service(request, p)
        entry = {"asked": request, "point": category.get("letter", ""), "words_in_common": score,
                 "text": (category.get("text") or "")[:180]}
        numbers.setdefault("matches", []).append(entry)
        (breaches if score >= 2 else weak if score == 1 else []).append((category, entry))
    if breaches:
        category, entry = breaches[0]
        letter = category.get("letter", "")
        waiver = _derogation(p, letter)
        return Finding("independence-monitor", asks, BREACH,
                       f"'{entry['asked']}' falls inside point ({letter}) of the prohibition"
                       f": {entry['text']}"
                       + (f" 5(3) lets a Member State derogate for {', '.join(waiver)} of them, which is a"
                          " decision this firm does not make for it." if waiver else ""),
                       numbers, _article(p, letter, category.get("text", "")))
    if weak:
        return Finding("independence-monitor", asks, HOLD,
                       f"{', '.join(repr(e['asked']) for _, e in weak)} share one word with the prohibition"
                       f" and no more, which is not enough for this firm to either forbid the work or clear"
                       f" it.", numbers, cite, "audit-committee-liaison")
    return Finding("independence-monitor", asks, CLEAR,
                   "None of the requested services matches the words of the prohibition, so Article 5(1)"
                   " does not forbid them.", numbers, cite, "audit-committee-liaison")


def non_audit_assessor(case: Case, p: Priors) -> Finding:
    """The fee ratio. The same arithmetic is done in bytecode; this is the one that explains it."""
    asks = "is the non-audit fee within the cap"
    cap = p.value("non_audit_fee_cap_percent")
    cite = p.cite("non_audit_fee_cap_percent")
    ratio = case.non_audit_percent()
    numbers = {"audit_fee_cents": case.audit_fee_cents, "non_audit_fee_cents": case.non_audit_fee_cents,
               "percent_of_audit_fee": ratio, "cap_percent": cap}
    if cap is None:
        return Finding("non-audit-assessor", asks, SILENT,
                       "No fee cap was derived from the corpus, so there is no ceiling to assess against.",
                       numbers, cite)
    if case.audit_fee_cents <= 0:
        return Finding("non-audit-assessor", asks, SILENT,
                       f"The ledger states no audit fee for {case.client}, so there is no ratio for the"
                       f" {cap:g}% ceiling to fall on and no agreement this figure can bind.",
                       numbers, cite)
    verdict = CLEAR if case.non_audit_fee_cents <= case.audit_fee_cents * cap / 100.0 else BREACH
    # The ratio in the words is rounded; the verdict above is not. At one cent past the ceiling the
    # two disagree in print - the file reads "70% against a 70% ceiling" and calls it a breach - so
    # the cents that decided it are filed alongside it, the way the dependence line files its own.
    return Finding("non-audit-assessor", asks, verdict,
                   f"Non-audit work is {ratio:g}% of the audit fee"
                   f" - {case.non_audit_fee_cents} of {case.audit_fee_cents} cents"
                   f" against a {cap:g}% ceiling{p.where('non_audit_fee_cap_percent')}.",
                   numbers, cite,
                   "engagement-partner" if verdict == CLEAR else "")


def fraud_risk_assessor(case: Case, p: Priors) -> Finding:
    """Economic dependence, which is a fraud risk before it is an independence problem."""
    asks = "does this client threaten the firm's own independence"
    floor = p.value("fee_dependence_percent")
    cite = p.cite("fee_dependence_percent")
    share = case.dependence_percent()
    numbers = {"firm_fee_from_client_cents": case.firm_fee_from_client_cents,
               "firm_total_fees_cents": case.firm_total_fees_cents, "percent_of_firm_fees": share,
               "dependence_percent": floor}
    if floor is None:
        return Finding("fraud-risk-assessor", asks, SILENT, "No dependence threshold was derived.",
                       numbers, cite)
    if case.firm_total_fees_cents <= 0:
        return Finding("fraud-risk-assessor", asks, SILENT,
                       f"The firm's own fee ledger is empty for {case.client}, so dependence on this"
                       f" client cannot be measured against the {floor:g}% threshold.", numbers, cite)
    # The verdict reads the cents, not the figure the file prints: rounding a ratio to two
    # places before comparing it would let a firm that is 0.004% dependent read as clear.
    verdict = BREACH if case.firm_fee_from_client_cents > case.firm_total_fees_cents * floor / 100.0 else CLEAR
    return Finding("fraud-risk-assessor", asks, verdict,
                   f"This client is {share:g}% of the firm's fees against a {floor:g}% threshold"
                   f" - {case.firm_fee_from_client_cents} of {case.firm_total_fees_cents} cents"
                   f"{p.where('fee_dependence_percent')}.", numbers, cite,
                   "engagement-partner" if verdict == CLEAR else "")


def aml_compliance_officer(case: Case, p: Priors) -> Finding:
    """How stale the beneficial-owner check is, against how long the register keeps its data."""
    asks = "is the client still identifiable from the record"
    years = p.value("aml_record_retention_years")
    cite = p.cite("aml_record_retention_years")
    numbers = {"kyc_checked_years_ago": case.kyc_checked_years_ago, "register_holds_years": years}
    if years is None:
        return Finding("aml-compliance-officer", asks, SILENT,
                       "The corpus states no retention period for beneficial-owner data.", numbers, cite)
    stale = case.kyc_checked_years_ago > years
    return Finding("aml-compliance-officer", asks, BREACH if stale else CLEAR,
                   f"The check is {case.kyc_checked_years_ago} years old and the register is kept for at"
                   f" least {years:g}{p.where('aml_record_retention_years')}.", numbers, cite)


def evidence_archivist(case: Case, p: Priors) -> Finding:
    """Whether the firm has promised to keep the file shorter than the record it rests on."""
    asks = "will the evidence outlive the file that cites it"
    years = p.value("aml_record_retention_years")
    cite = p.cite("aml_record_retention_years")
    numbers = {"file_retention_years": case.file_retention_years, "floor_years": years}
    if years is None:
        return Finding("evidence-archivist", asks, SILENT,
                       "No retention floor was derived, so the firm's own policy is the only rule.",
                       numbers, cite)
    if case.file_retention_years <= 0:
        return Finding("evidence-archivist", asks, SILENT,
                       f"{case.client}'s file states no retention period, so there is nothing here to"
                       f" compare with the {years:g}-year floor in the text.", numbers, cite)
    short = case.file_retention_years < years
    return Finding("evidence-archivist", asks, BREACH if short else CLEAR,
                   f"The file is kept for {case.file_retention_years} years where the text sets a floor of"
                   f" {years:g}{p.where('aml_record_retention_years')}.", numbers, cite)


def group_audit_coordinator(case: Case, p: Priors) -> Finding:
    """Is this a group audit at all, on the holding the Accounting Directive presumes?"""
    asks = "is this a group audit requiring instructions to component auditors"
    presumed = p.value("participation_presumed_percent")
    cite = p.cite("participation_presumed_percent")
    band = p.band("large undertakings")
    criteria = {"balance_sheet_eur": ("balance sheet total", band.get("balance_sheet_total_eur")),
                "net_turnover_eur": ("net turnover", band.get("net_turnover_eur"))}
    values = {"balance_sheet_eur": case.balance_sheet_eur, "net_turnover_eur": case.turnover_eur}
    over = [label for key, (label, limit) in criteria.items() if limit and values[key] > limit]
    headcount = bool(band.get("average_employees")) and case.employees > band["average_employees"]
    numbers = {"parent_holding_percent": case.parent_holding_percent, "presumed_percent": presumed,
               "declared_group": case.is_group, "large_over_criteria": over,
               "large_limits_eur": {key: limit for key, (_label, limit) in criteria.items()},
               "large_employee_floor": band.get("average_employees"),
               "employees_over": headcount, "employees": case.employees}
    if presumed is None or not band:
        return Finding("group-audit-coordinator", asks, SILENT,
                       "Neither the presumed holding nor the size ladder was derived from the corpus.",
                       numbers, cite)
    large = len(over) >= 2 or (headcount and len(over) >= 1)
    large_by = " and ".join(list(over) + (["average headcount"] if headcount else []))
    size = f"large by {large_by}" if large_by else "no large-undertaking criterion met"
    if case.parent_holding_percent >= presumed and large:
        return Finding("group-audit-coordinator", asks, CLEAR,
                       f"{case.parent_holding_percent:g}% reaches the {presumed:g}% presumption of a"
                       f" parent undertaking{p.where('participation_presumed_percent')} and the client is"
                       f" {size}, so component auditors must be instructed.", numbers,
                       p.cite("participation_presumed_percent"), "engagement-partner")
    return Finding("group-audit-coordinator", asks, HOLD,
                   f"A {case.parent_holding_percent:g}% holding against the {presumed:g}% presumption"
                   f"{p.where('participation_presumed_percent')} and {size}: the text does not let this"
                   f" firm say whether a group audit is being performed.",
                   numbers, cite)


def audit_committee_liaison(case: Case, p: Priors) -> Finding:
    """Article 5(4): everything the prohibition does not name still belongs to the committee."""
    asks = "has the audit committee approved the non-audit work"
    approval = p.services.get("approval") or ""
    cite = _article(p, "4", approval)
    numbers = {"non_audit_services": list(case.non_audit_services), "is_public_interest_entity": case.is_pie}
    if not approval:
        return Finding("audit-committee-liaison", asks, SILENT,
                       "The corpus does not carry the approval sentence this question needs.", numbers, cite)
    if not case.non_audit_services:
        return Finding("audit-committee-liaison", asks, CLEAR,
                       "There is no non-audit service for a committee to approve.", numbers, cite)
    if not case.is_pie:
        return Finding("audit-committee-liaison", asks, SILENT,
                       f"Article 5(4) makes the audit committee's approval a condition of a non-audit"
                       f" service to a public-interest entity, and {case.client} is not one, so this firm"
                       f" has no committee to ask.", numbers, cite)
    return Finding("audit-committee-liaison", asks, HOLD,
                   f"A service outside the prohibition may still be provided only subject to the approval"
                   f" of the audit committee, and no agent of this firm can give that approval."
                   f" {approval[:180]}", numbers, cite, "engagement-partner")


def tender_administrator(case: Case, p: Priors) -> Finding:
    """When the firm has to go and compete for the client it already has."""
    asks = "is a competitive tender due"
    initial = p.value("rotation_initial_max_years")
    cite = p.cite("rotation_initial_max_years")
    numbers = {"years_auditing": case.years_auditing, "tender_held": case.tender_held,
               "initial_max_years": initial, "is_public_interest_entity": case.is_pie}
    if initial is None:
        return Finding("tender-administrator", asks, SILENT,
                       "No initial term was derived, so no tender date can be computed.", numbers, cite)
    if not case.is_pie:
        return Finding("tender-administrator", asks, SILENT,
                       "Article 17's tender requirement is engaged by a public-interest entity, and this"
                       " client is not one.", numbers, cite)
    if case.tender_held:
        return Finding("tender-administrator", asks, CLEAR,
                       f"A tender was already held at {case.years_auditing} years, so the longer ceiling"
                       f" applies{p.where('rotation_with_tender_max_years')}.", numbers,
                       p.cite("rotation_with_tender_max_years"))
    if case.years_auditing >= initial - 1:
        return Finding("tender-administrator", asks, CLEAR,
                       f"{case.years_auditing} years in: a tender must be held before the {initial:g}-year"
                       f" ceiling closes{p.where('rotation_initial_max_years')}.", numbers, cite)
    return Finding("tender-administrator", asks, HOLD,
                   f"{case.years_auditing} years of a {initial:g}-year initial term: no tender is due yet,"
                   f" and nothing here says when the firm will want one{p.where('rotation_initial_max_years')}.",
                   numbers, cite)


def materiality_reviewer(case: Case, p: Priors) -> Finding:
    """The question the corpus cannot answer, kept in the firm so nobody quietly guesses it.

    The silence is derived, not written: if a future corpus states a percentage, this role starts
    doing the arithmetic and still hands the judgement to a person, because the figure that is
    material to one set of statements is not material to the next and no regulation decides it.
    """
    asks = "what is material to these financial statements"
    name = "materiality_percent_of_turnover"
    prior = p.prior(name)
    percent = p.value(name)
    materiality = round(case.turnover_eur * percent / 100.0, 2) if percent and case.turnover_eur else None
    numbers = {"turnover_eur": case.turnover_eur, "materiality_percent_of_turnover": prior.get("value"),
               "materiality_eur": materiality, "state": prior.get("state", "missing")}
    cite = p.cite(name) or {"celex": "", "article": "", "state": str(prior.get("state", "missing")),
                            "quote": str(prior.get("note") or "")[:300]}
    if percent is None:
        return Finding("materiality-reviewer", asks, SILENT,
                       "No EU statute in the harvested corpus states a materiality percentage, so this"
                       " firm has no lawful number to apply and will not supply one of its own.",
                       numbers, cite)
    if materiality is None:
        return Finding("materiality-reviewer", asks, SILENT,
                       f"The text would give a percentage but {case.client}'s file gives no turnover to"
                       f" apply it to.", numbers, cite)
    return Finding("materiality-reviewer", asks, HOLD,
                   f"{percent:g}% of a turnover of EUR {case.turnover_eur:,.0f} is EUR {materiality:,.0f},"
                   f" and an auditing standard makes the choice of percentage the auditor's judgement"
                   f" rather than a figure this firm may set{p.where(name)}.", numbers, cite,
                   "engagement-partner")


def quality_review_partner(case: Case, p: Priors) -> Finding:
    """A second partner looks at the file. The text says a review exists; it does not say when."""
    asks = "does this file need an independent quality review"
    numbers = {"is_public_interest_entity": case.is_pie, "non_audit_services": list(case.non_audit_services),
               "state": "not_in_corpus"}
    return Finding("quality-review-partner", asks, HOLD,
                   f"Whether a reviewer is needed for {case.client} is that partner's judgement rather than"
                   f" a threshold in the corpus, so this agreement stays open until a person signs it.",
                   numbers, {"state": "not_in_corpus", "quote": str(p.uncalibrated())},
                   "engagement-partner")


QUESTIONS: tuple[tuple[str, Callable[[Case, Priors], Finding]], ...] = (
    ("engagement-partner", engagement_partner),
    ("rotation-tracker", rotation_tracker),
    ("independence-monitor", independence_monitor),
    ("non-audit-assessor", non_audit_assessor),
    ("fraud-risk-assessor", fraud_risk_assessor),
    ("aml-compliance-officer", aml_compliance_officer),
    ("evidence-archivist", evidence_archivist),
    ("group-audit-coordinator", group_audit_coordinator),
    ("audit-committee-liaison", audit_committee_liaison),
    ("tender-administrator", tender_administrator),
    ("materiality-reviewer", materiality_reviewer),
    ("quality-review-partner", quality_review_partner),
)

ROLES = tuple(role for role, _ in QUESTIONS)


# ------------------------------------------------------------------------ the words layer

class RuleWords:
    """The deterministic voice: a finding is restated, never improved."""

    name = "rules"

    def phrase(self, finding: Finding, case: Case) -> Finding:
        return finding

    def describe(self) -> dict[str, Any]:
        return {"route": "rules", "why": "no model endpoint is configured, so the firm uses its own words"}


class ModelWords:
    """Muse for the sentence, the corpus for the number.

    `narrate` is given the figures a finding was computed from, and every number in what comes
    back has to be one of them. A reply that invents one is dropped and the rule's own sentence is
    used instead - and the route says that happened, because a fallback nobody can see is a bug
    report nobody reads.

    This is the *captioning* layer, and it is only reached when no `Judge` is wired: with a judge
    present the model has already written the sentence, verified it against the statute it was shown,
    and asking a second endpoint to restate it would spend a request to lose the quote.
    """

    name = "model"

    def __init__(self, planner: Any) -> None:
        self.planner = planner

    def phrase(self, finding: Finding, case: Case) -> Finding:
        ask = (f"You are the {finding.role} of an EU statutory audit firm writing one line of the"
               f" engagement file about {case.client}. The verdict is already made ({finding.verdict})"
               f" and every figure you may use is in FACTS. Say what it means in one sentence; add no"
               f" number and change no threshold.")
        words = self.planner.narrate(ask, [dict(finding.numbers, verdict=finding.verdict)],
                                     {"voice_prompt": ask})
        route = getattr(self.planner, "last_route", "") or self.planner.route
        if not words.strip():
            return finding.with_words(finding.sentence, "rules (the model returned no words)")
        if route.startswith("rules"):
            return finding.with_words(finding.sentence, route)
        return finding.with_words(words.strip(), route)

    def describe(self) -> dict[str, Any]:
        return {"route": self.planner.route, "provider": getattr(self.planner, "provider", "")}


class Firm:
    """Asks the twelve questions of a case, then turns the answers into traffic on the chain."""

    def __init__(self, priors: Priors | None = None, words: Any = None, judge: Any = None) -> None:
        self.priors = priors or Priors.load()
        self.words = words or RuleWords()
        self.judge = judge

    @classmethod
    def from_env(cls, priors: Priors | None = None) -> "Firm":
        """Muse decides if this machine is configured for it; otherwise the firm's own rules do.

        `Judge.from_env` is the whole decision: it returns None when no endpoint has a key, and
        `Judge.ask` returns None when the harvested text is not on the machine either - which is the
        case that matters, because a judgement nothing can be checked against is not one this firm is
        entitled to file. Both leave `judge` None and the deterministic answers speaking for
        themselves, on a route that says so.
        """
        from twin.audit.judge import Judge

        return cls(priors, judge=Judge.from_env())

    def review(self, case: Case) -> list[Finding]:
        """Every role, once, in roster order. No chain touched."""
        found = []
        for role, answer in QUESTIONS:
            base = answer(case, self.priors)
            if base.role != role:
                raise AssertionError(f"{role} answered as {base.role}")
            found.append(self._record(base, case))
        return found

    def _record(self, base: Finding, case: Case) -> Finding:
        """The finding that goes in the engagement file.

        With a judge, the rule below is the fallback and the model's checked judgement is the answer;
        without one, the rule is the answer and a model may only re-word it. Both branches keep the
        deterministic `base` in hand, because the thing being substituted for must survive to be
        substituted in.
        """
        if self.judge is not None:
            from twin.audit.judge import facts_of

            return self.judge.judge(base.role, base.asks, facts_of(case), lambda: base)
        return self.words.phrase(base, case)

    def describe(self) -> dict[str, Any]:
        """Whose judgements the firm is speaking with, and what it can check them against."""
        if self.judge is not None:
            return self.judge.describe()
        return self.words.describe()

    def transact(self, case: Case, bus: Bus) -> dict[str, Any]:
        """One case through the firm and onto the chain.

        The order of the writes is the point of the exercise: a finding only binds anybody once
        the counterparty has accepted it, and a finding that reached `Attested` is a finding a
        named human still has to sign. This method never countersigns, because it has no key that
        could mean anything to the registry.
        """
        findings = self.review(case)
        opened = []
        for finding in findings:
            if not finding.binding:
                continue
            terms = f"{case.client}: {finding.sentence}"
            proposed = bus.send("propose", from_role=finding.role, to_role=finding.to_role,
                                subject=finding.asks, terms=terms,
                                amount_cents=case.audit_fee_cents,
                                non_audit_cents=case.non_audit_fee_cents)
            steps = [proposed.as_dict()]
            agreement = proposed.agreement
            if proposed.ok:
                accepted = bus.send("accept", from_role=finding.to_role, agreement=agreement)
                steps.append(accepted.as_dict())
                if accepted.ok:
                    attested = bus.send("attest", from_role=finding.role, agreement=agreement,
                                        evidence=terms)
                    steps.append(attested.as_dict())
            opened.append({"role": finding.role, "to_role": finding.to_role, "verdict": finding.verdict,
                           "agreement": agreement, "steps": steps, "state": steps[-1]["state"]})
        summary = {
            "client": case.client,
            "route": self.words.describe(),
            "findings": [f.as_dict() for f in findings],
            "counts": {verdict: sum(1 for f in findings if f.verdict == verdict)
                       for verdict in (CLEAR, BREACH, HOLD, SILENT)},
            "agreements": opened,
            "waiting_on_humans": bus.waiting_on_humans(),
        }
        if bus.store is not None and bus.user_id:
            bus.store.append_log(bus.user_id, bus.day, "audit_review", {
                "client": case.client, "opened": len(opened), "counts": summary["counts"],
                "blocked": [f["role"] for f in summary["findings"] if f["verdict"] == BREACH],
                "silent": [f["role"] for f in summary["findings"] if f["verdict"] == SILENT],
                "waiting": len(summary["waiting_on_humans"]), "route": summary["route"]["route"],
            })
        return summary
