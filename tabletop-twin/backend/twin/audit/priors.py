"""Derives the audit agents' thresholds from the harvested text.

Every number here is found in a fetched sentence, and carries the sentence with it. That
is the whole point of this module: a rule the firm enforces but cannot quote is a rule
somebody invented. Where the corpus does not state a figure - materiality is an auditing
standard's judgement, not a number in a regulation - the prior comes back unset and says
so, and the agent that would have used it runs on a documented default that is labelled
uncalibrated instead of quietly looking like law.

`python -m twin.audit.calibrate` rebuilds `data/priors.json` from whatever is in the
corpus directory, so the numbers move when the law is amended and nobody has to remember
to edit a constant.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from twin.audit.corpus import CORPUS_DIR, DATA_DIR, corpus_place, measures, sentences

UNCALIBRATED = "uncalibrated"


@dataclass(frozen=True)
class Rule:
    """A number the firm enforces, described by the words that surround it.

    Keywords select sentences rather than article numbers, because the consolidated text
    renumbers what an amendment inserted. Anchoring on a phrase survives that; anchoring on
    "Article 9" would have found the wrong rule.
    """

    name: str
    keywords: tuple[str, ...]
    measure: str
    within: int = 320
    requires: tuple[str, ...] = ()
    adjacent: str = ""
    pick: str = "mode"
    note: str = ""

    def matches(self, sentence: str) -> bool:
        low = sentence.lower()
        if not all(k in low for k in self.keywords):
            return False
        return all(k in low for k in self.requires)


@dataclass(frozen=True)
class Prior:
    name: str
    value: float | None
    unit: str
    celex: str
    article: str
    quote: str
    hits: int
    distinct: list[float] = field(default_factory=list)
    note: str = ""

    @property
    def calibrated(self) -> bool:
        return self.value is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name, "value": self.value, "unit": self.unit, "celex": self.celex,
            "article": self.article, "quote": self.quote, "hits": self.hits,
            "distinct": self.distinct, "note": self.note,
            "state": "calibrated" if self.calibrated else UNCALIBRATED,
        }


# What an auditing firm actually has to obey, as numbers.
RULES: tuple[Rule, ...] = (
    Rule("rotation_initial_max_years", ("initial engagement", "shall exceed"), "duration_years",
         pick="max",
         note="Article 17's ceiling on how long one firm may hold one listed or public-interest client. "
              "Keyed on 'shall exceed' because the derogation two paragraphs down also names the initial "
              "engagement and a maximum duration, and states neither of them as the rule."),
    Rule("rotation_with_tender_max_years", ("tender", "maximum duration"), "duration_years",
         pick="max",
         note="The outer ceiling on how long one firm may hold one public-interest client, reached only "
              "where the tender involved more than one firm or voluntary early tendering. One sentence "
              "states both the 20-year tier and this bound, and only the larger is an absolute limit."),
    Rule("rotation_tendered_max_years", ("public tendering process", "maximum duration"),
         "duration_years", pick="min",
         note="The extension an ordinary competitive tender buys. The same sentence states it as the "
              "smaller of two figures, so the rule that wants it says 'min'."),
    Rule("key_partner_rotation_years", ("key audit partner", "rotate"), "duration_years",
         pick="max",
         note="How long the signing partner may keep signing for the same client."),
    Rule("partner_cooling_off_years", ("not participate again",), "duration_years",
         note="How long a key audit partner of a public-interest entity must stay off the audit before "
              "returning to it. The Regulation states it as a plain 'before three years have elapsed', "
              "with no 'at least' in the sentence at all, so keying on that phrase would have missed it."),
    Rule("auditor_return_cooldown_years", ("before a period of at least",), "duration_years",
         pick="min",
         note="The Directive's floor for any statutory auditor returning to an audit they worked on. The "
              "sentence gives a band - one year generally, two where the audited entity is a "
              "public-interest entity - and the Regulation's three years is stricter for the partner of "
              "such an entity, so each agent asks the text for the one that fits its client."),
    Rule("non_audit_fee_cap_percent", ("total fees", "non-audit services"), "percent",
         note="The cap on what a firm may charge the same client for everything except the audit."),
    Rule("fee_dependence_percent", ("total fees received from a public-interest entity",), "percent",
         note="Share of a firm's fees from one client that counts as dependence and must be addressed."),
    Rule("delegation_period_years", ("delegated acts", "conferred"), "duration_years",
         note="How long the Commission's power to write the auditing standards lasts."),
    Rule("size_balance_sheet_ceiling_eur", ("shall not exceed", "balance sheet total"), "amount_eur",
         adjacent="for the balance sheet total",
         note="The most a Member State may raise its own small-undertaking balance-sheet line."),
    Rule("size_net_turnover_ceiling_eur", ("shall not exceed", "net turnover"), "amount_eur",
         adjacent="for the net turnover",
         note="The same ceiling applied to the turnover line."),
    Rule("participation_presumed_percent", ("participating interest", "presumed"), "percent",
         note="The holding that makes one undertaking the other's parent for group-audit purposes."),
    Rule("reporting_entity_employee_floor", ("public-interest entities exceeding", "employees"), "count",
         note="Headcount at which a public-interest entity owes the sustainability statement at all."),
    Rule("aml_record_retention_years", ("beneficial owner",), "duration_years",
         pick="min",
         note="The floor on how long the register the KYC agent checks against keeps its data. "
              "The sentence gives a band - 'at least five years and no more than 10' - and the floor "
              "is the number an agent can rely on."),
    # Materiality is an auditor's judgement under an auditing standard, not a figure in EU
    # law. It is listed so the run proves the absence rather than hiding it.
    Rule("materiality_percent_of_turnover", ("materiality",), "percent",
         note="No EU statute in the corpus states a materiality percentage."),
)


def load_statutes(corpus: Path | None = None) -> list[dict[str, Any]]:
    directory = (corpus or CORPUS_DIR) / "statutes"
    if not directory.exists():
        return []
    out = []
    for path in sorted(directory.glob("*.json")):
        try:
            out.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return out


def window(sentence: str, start: int, within: int) -> str:
    """The sentence, shortened for a panel without ever cutting the number out of it.

    A quote is the proof, and a proof that stopped short of the figure it vouches for proves
    nothing: the twenty-four-year ceiling sits at the far end of the sentence that states it.
    """
    limit = within or 320
    if len(sentence) <= limit:
        return sentence
    head = max(0, min(start - limit // 4, len(sentence) - limit))
    return sentence[head:head + limit]


def find(rule: Rule, statutes: list[dict[str, Any]]) -> Prior:
    """Search every article of every fetched statute for the number this rule names."""
    hits: list[dict[str, Any]] = []
    for document in statutes:
        for article in document.get("articles", []):
            text = article.get("text", "")
            if rule.within and len(text) > 400_000:
                continue
            for sentence in sentences(text):
                if not rule.matches(sentence):
                    continue
                for number in measures(sentence):
                    if number["measure"] != rule.measure:
                        continue
                    if number["value"] != number["value"]:  # NaN
                        continue
                    hits.append({
                        "celex": document["celex"], "article": article["article"],
                        "value": number["value"], "unit": number["unit"],
                        "start": number.get("start", 0), "end": number.get("end", 0),
                        "sentence": sentence,
                    })
    if not hits:
        return Prior(rule.name, None, rule.measure, "", "", "", 0, [], rule.note)
    distinct = sorted({h["value"] for h in hits})
    if rule.adjacent:
        # "shall not exceed EUR 6 000 000 for the balance sheet total and EUR 12 000 000 for
        # the net turnover" is one sentence with two ceilings. The rule that wants the second
        # one asks for the number sitting just before its own words.
        near = []
        for hit in hits:
            position = hit["sentence"].lower().find(rule.adjacent)
            if position >= 0 and hit["end"] <= position:
                near.append((position - hit["end"], hit))
        if not near:
            return Prior(rule.name, None, rule.measure, "", "", "", len(hits), distinct,
                         rule.note + f" (no number found immediately before '{rule.adjacent}')")
        chosen = min(near, key=lambda pair: pair[0])[1]
        return Prior(rule.name, chosen["value"], rule.measure, chosen["celex"], chosen["article"],
                     window(chosen["sentence"], chosen["start"], rule.within), len(hits),
                     distinct, rule.note)
    # How a rule reads a passage that contains several numbers of its kind. "a maximum
    # period of seven years" and "at least four years" are both durations, and the one that
    # is a ceiling is not the one that is a floor, so each rule says which it is.
    if rule.pick == "max":
        best = max(distinct)
    elif rule.pick == "min":
        best = min(distinct)
    else:
        counts: dict[float, int] = {}
        for hit in hits:
            counts[hit["value"]] = counts.get(hit["value"], 0) + 1
        # The most-repeated reading wins; ties go to the larger number, because in this
        # corpus the general rule is the longer period and the derogation is the shorter one.
        best = max(counts.items(), key=lambda kv: (kv[1], kv[0]))[0]
    chosen = next(h for h in hits if h["value"] == best)
    return Prior(rule.name, best, rule.measure, chosen["celex"], chosen["article"],
                 window(chosen["sentence"], chosen["start"], rule.within), len(hits), distinct,
                 rule.note)


BAND_NAMES = ("micro-undertakings", "small undertakings", "medium-sized undertakings",
              "large undertakings", "small groups", "medium-sized groups", "large groups")
EURO = re.compile(r"EUR\s*([\d][\d .,]{2,15})", re.I)
HEADCOUNT = re.compile(r"employees[^.\n]{0,40}?:\s*(\d{1,4})", re.I)


def derive_bands(statutes: list[dict[str, Any]]) -> dict[str, Any]:
    """The EU size ladder, read out of the article that defines it.

    Article 3 of the Accounting Directive prints each class as a label followed by three
    criteria in a fixed order - balance sheet total, net turnover, average employees. A
    keyword search cannot separate "small" from "medium" here because the amounts sit in
    their own fragment lines, so this walks forward from each label instead. The order is
    recorded as it was found rather than assumed, and the raw list of amounts travels with
    the band so a reader can check which number got called what.
    """
    for document in statutes:
        for article in document.get("articles", []):
            text = article.get("text", "")
            if "categories of undertakings" not in text.lower():
                continue
            low = text.lower()
            bands: dict[str, Any] = {}
            for name in BAND_NAMES:
                start = low.find(name)
                if start < 0:
                    continue
                window = text[start:start + 620]
                amounts = [float(m.replace(" ", "").replace("\u00a0", "").replace(",", "."))
                           for m in EURO.findall(window)]
                head = HEADCOUNT.search(window)
                bands[name] = {
                    "balance_sheet_total_eur": amounts[0] if amounts else None,
                    "net_turnover_eur": amounts[1] if len(amounts) > 1 else None,
                    "average_employees": float(head.group(1)) if head else None,
                    "amounts_in_order": amounts[:4],
                    "celex": document["celex"], "article": article["article"],
                    "quote": re.sub(r"\s+", " ", window)[:300],
                }
            return {"source": document["celex"], "article": article["article"], "bands": bands}
    return {"source": "", "article": "", "bands": {}}


SERVICES_INTRO = "prohibited non-audit services shall mean"
LETTER = re.compile(r"^\(([a-z]+)\)$")
# A range in Article 5(3) repeats the letter before its end point - "(a) (iv) to (a) (vii)" -
# so the optional second "(a)" has to be allowed for or the middle of the range is lost.
POINT = re.compile(
    r"\(([a-z])\)"
    r"(?:\s*\(([ivx]+)\)"
    r"(?:\s+to\s+(?:\([a-z]\)\s*)?\(([ivx]+)\))?"
    r")?"
)
ROMAN = ("i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x", "xi", "xii")


def derive_services(statutes: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """The services an auditor may not sell to an entity it audits, read out of Article 5.

    The Audit Regulation prints the prohibition as a lettered list inside one article, so this
    walks that list instead of carrying a copy of it. Two neighbouring sentences come back with
    it because both change what an answer means: 5(3) lets a Member State derogate for named
    sub-points, and 5(4) sends every service the list does not prohibit to the audit committee.
    Between them they are why the firm's independence agent can refuse a job but cannot approve
    one.
    """
    for document in (statutes if statutes is not None else load_statutes()):
        for article in document.get("articles", []):
            text = article.get("text", "")
            low = text.lower()
            if SERVICES_INTRO not in low or "prohibition of the provision of non-audit services" not in low:
                continue
            categories: list[dict[str, Any]] = []
            category: dict[str, Any] | None = None
            sub: dict[str, Any] | None = None
            wanted = "a"
            for line in text[low.find(SERVICES_INTRO):].splitlines():
                stripped = line.strip().strip("\t")
                if not stripped or stripped.lower().startswith(SERVICES_INTRO):
                    continue
                if re.match(r"^2\.\s", stripped):
                    break
                marker = LETTER.match(stripped)
                if marker and marker.group(1) == wanted:
                    category = {"letter": wanted, "title": "", "subs": [], "text": ""}
                    categories.append(category)
                    sub, wanted = None, chr(ord(wanted) + 1)
                    continue
                if category is None:
                    continue
                if marker and marker.group(1) in ROMAN:
                    sub = {"letter": marker.group(1), "text": ""}
                    category["subs"].append(sub)
                    continue
                target = sub if sub is not None else category
                target["text"] = (target["text"] + " " + stripped).strip()
                if target is category and not category["title"]:
                    category["title"] = stripped.rstrip(";:.")
            if not categories:
                continue
            derogation = next((s for s in sentences(text) if "by way of derogation" in s.lower() and "points" in s.lower()), "")
            # Only the list of points is a list of points. The sentence runs on into the three
            # conditions the derogation is subject to, and those are lettered (a), (b) and (c)
            # too - reading them as services would mark bookkeeping derogable.
            where = derogation.lower().find("referred to in points")
            tail = derogation[where + len("referred to in points"):] if where >= 0 else ""
            stop = tail.lower().find("provided that")
            named = tail[:stop].strip(" ,.") if stop >= 0 else tail.strip(" ,.")
            points: dict[str, list[str]] = {}
            for letter, first, last in POINT.findall(named):
                span = ROMAN[ROMAN.index(first):ROMAN.index(last) + 1] if last else ([first] if first else [])
                points.setdefault(letter, []).extend(span)
            return {
                "celex": document["celex"], "article": article["article"],
                "categories": categories,
                # The chapeau says whose audits the list binds, which is the difference between
                # a prohibition and a policy preference for everything else the firm audits.
                "scope": next((s for s in sentences(text)
                               if "shall not directly or indirectly provide" in s.lower()), ""),
                "derogation": {
                    "quote": derogation, "points_text": named,
                    "points": {k: sorted(set(v), key=ROMAN.index) for k, v in sorted(points.items())},
                },
                "approval": next((s for s in sentences(text)
                                  if "subject to the approval of the audit committee" in s.lower()), ""),
            }
    return {"celex": "", "article": "", "categories": [], "scope": "",
            "derogation": {"quote": "", "points_text": "", "points": {}}, "approval": ""}


def derive(statutes: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    statutes = statutes if statutes is not None else load_statutes()
    priors = [find(rule, statutes) for rule in RULES]
    return {
        "derived_from": {
            "statutes": len(statutes),
            "articles": sum(len(s.get("articles", [])) for s in statutes),
            "corpus_dir": corpus_place(),
        },
        "uncalibrated": [p.name for p in priors if not p.calibrated],
        "priors": {p.name: p.to_dict() for p in priors},
        "size_bands": derive_bands(statutes),
        "non_audit_services": derive_services(statutes),
    }


def main(argv: list[str]) -> int:
    if argv and argv[0] in {"-h", "--help"}:
        print("usage: python -m twin.audit.calibrate [--json]\n"
              "  re-derives every audit threshold from the harvested statute text")
        return 0
    result = derive()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "priors.json").write_text(
        json.dumps(result, indent=1, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    if "--json" in argv:
        print(json.dumps(result, indent=1, ensure_ascii=False))
    else:
        for name, prior in sorted(result["priors"].items()):
            flag = "ok " if prior["state"] == "calibrated" else "-- "
            where = f"{prior['celex']} art {prior['article']}" if prior["celex"] else "not in the corpus"
            print(f"{flag}{name:34s} {str(prior['value']):>12} {prior['unit']:14s} {where}"
                  f"  ({prior['hits']} hits, {len(prior['distinct'])} distinct)")
        print(f"\nuncalibrated: {result['uncalibrated'] or 'none'}")
        bands = result["size_bands"]
        print(f"size ladder from {bands['source']} art {bands['article']}:")
        for name, band in bands["bands"].items():
            print(f"  {name:28s} balance sheet {str(band['balance_sheet_total_eur']):>14}"
                  f"  turnover {str(band['net_turnover_eur']):>14}  employees {band['average_employees']}")
        services = result["non_audit_services"]
        letters = ", ".join(c["letter"] for c in services["categories"])
        print(f"\nprohibited non-audit services from {services['celex']} art {services['article']}: "
              f"{len(services['categories'])} categories ({letters})")
        for category in services["categories"]:
            print(f"  ({category['letter']}) {category['title'][:74]}")
        print(f"  5(3) derogation covers {services['derogation']['points'] or 'nothing'}")
        print(f"  5(4) approval sentence: {'found' if services['approval'] else 'NOT FOUND'}")
    return 0 if result["priors"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
