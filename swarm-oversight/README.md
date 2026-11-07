# swarm-oversight

Our starting point for the Apart Swarm Alignment hackathon, track 4 (multi-agent oversight).

Tabletop Twin already gives one agent a spending limit and a guard that says no. This asks the next question: what happens when there are several agents, each one staying inside its own limit, and together they do something none of them was allowed to do alone? A per-agent guard can't see that. You have to watch the swarm.

There are three parts. `scenarios.py` builds seeded action logs: ordinary background spending plus a planted attack, with the attack's actions recorded as ground truth. `monitor.py` reads a log in order and raises flags for one agent going over its limit, a split payment (several agents paying one payee in a short window, together over the cap) and a relay (an agent near its limit hands money to a quiet agent, who spends it). `harness.py` runs the monitor over many seeds and reports recall, false alarm rate and how late the flag came.

    pip install -e .[dev]
    pytest
    python -m swarm_oversight.harness --seeds 200

Right now the monitor catches every planted attack with no false alarms. That's because the attacks are naive. The next step is variants that try to slip past: splits spread wider than the window, relays through two hops, payee names that change slightly. Then we can show where the monitor breaks, and that's the more interesting part of the report.

Everything is the standard library, no model calls, so a score can be reproduced from the seed alone.
