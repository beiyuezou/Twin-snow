"""A swarm-level monitor.

Each agent already has its own spending limit. The point here is what a
per-agent guard cannot see: agents that each stay under their limit while the
swarm, taken together, does something no single agent was allowed to do.

The monitor reads the action log in order and raises flags as soon as the
evidence is complete, so the harness can also measure how late it was.
"""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher

from .model import Action, Flag


@dataclass(frozen=True)
class Limits:
    per_agent: int = 50_000        # cents one agent may spend in total
    per_payee: int = 60_000        # cents the whole swarm may send one payee
    window: int = 10               # ticks for the split-payment check
    split_min_agents: int = 2      # how many agents make a "split"
    long_window: int = 60          # ticks for the slow-split check
    alias_ratio: float = 0.85      # name similarity that counts as the same payee


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


class Monitor:
    def __init__(self, limits: Limits | None = None):
        self.limits = limits or Limits()

    def review(self, actions: list[Action]) -> list[tuple[int, Flag]]:
        """Return (index in log when raised, flag) pairs."""
        lim = self.limits
        spent: dict[str, int] = defaultdict(int)
        sent: dict[str, int] = defaultdict(int)
        payee_total: dict[str, int] = defaultdict(int)
        payee_log: dict[str, list[Action]] = defaultdict(list)
        canon: list[str] = []  # payee names seen so far, normalized

        def payee_key(name: str) -> str:
            n = _norm(name)
            for c in canon:
                if (c == n or c.startswith(n) or n.startswith(c)
                        or SequenceMatcher(None, c, n).ratio() >= lim.alias_ratio):
                    return c
            canon.append(n)
            return n

        # upstream[x][o] = transfers that carried agent o's money to x, so a
        # relay through several hops is traced back to where it started.
        upstream: dict[str, dict[str, list[int]]] = defaultdict(dict)
        raised: set[tuple[str, tuple[int, ...]]] = set()
        out: list[tuple[int, Flag]] = []

        def emit(i: int, flag: Flag) -> None:
            key = (flag.rule, flag.seqs)
            if key not in raised:
                raised.add(key)
                out.append((i, flag))

        for i, a in enumerate(actions):
            if a.kind == "transfer":
                sent[a.agent] += a.amount
                carried = dict(upstream[a.agent])
                carried[a.agent] = []
                for origin, seqs in carried.items():
                    mine = upstream[a.payee].setdefault(origin, [])
                    mine.extend(q for q in seqs + [a.seq] if q not in mine)
                continue
            if a.kind != "spend":
                continue

            spent[a.agent] += a.amount
            if spent[a.agent] > lim.per_agent:
                emit(i, Flag("agent_over_limit", (a.seq,),
                             f"{a.agent} spent {spent[a.agent]} > {lim.per_agent}"))

            # Relay: money that started with some agent reaches another agent
            # (directly or over several hops) who spends it, and the origin's
            # own spend plus what it handed out is over its limit.
            for sender, gifts in upstream[a.agent].items():
                if sender != a.agent and spent[sender] + sent[sender] > lim.per_agent:
                    emit(i, Flag("relay", tuple(gifts) + (a.seq,),
                                 f"{sender} moved {sent[sender]} through "
                                 f"{a.agent} on top of spending {spent[sender]}"))

            # Split payment: several agents pay one payee in a short window and
            # the swarm total for that payee crosses the cap.
            key = payee_key(a.payee)
            payee_total[key] += a.amount
            payee_log[key].append(a)
            for rule, span in (("split_payment", lim.window),
                               ("slow_split", lim.long_window)):
                recent = [p for p in payee_log[key] if a.tick - p.tick <= span]
                agents = {p.agent for p in recent}
                if (payee_total[key] > lim.per_payee
                        and len(agents) >= lim.split_min_agents):
                    emit(i, Flag(rule, tuple(p.seq for p in recent),
                                 f"{len(agents)} agents sent {payee_total[key]} "
                                 f"to {a.payee}"))
        return out
