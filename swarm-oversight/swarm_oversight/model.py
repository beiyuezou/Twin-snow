"""The few records the monitor and the scenarios share."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Action:
    """One thing an agent did. `kind` is "spend" (money leaves the swarm) or
    "transfer" (money moves from one agent's wallet to another's)."""

    seq: int
    agent: str
    kind: str
    amount: int  # cents, so sums are exact
    payee: str
    tick: int


@dataclass(frozen=True)
class Flag:
    rule: str
    seqs: tuple[int, ...]
    reason: str


@dataclass
class Scenario:
    name: str
    seed: int
    actions: list[Action]
    # seqs of the actions that belong to the misbehaviour; empty for benign runs
    attack: set[int] = field(default_factory=set)
