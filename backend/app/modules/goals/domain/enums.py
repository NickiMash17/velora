"""Enum type for the Goals domain.

`StateMachines.md §4` defines the full lifecycle
`proposed → active ⇄ at_risk → achieved`, plus `abandoned`. Per the M5
Step 3 plan's Finding 2 (resolved): only `proposed`/`active` are reachable
via any M5 endpoint — the other three values exist here for forward
compatibility with that state machine only, never written by this
checkpoint's code.
"""

from __future__ import annotations

import enum


class GoalStatus(enum.StrEnum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    AT_RISK = "at_risk"
    ACHIEVED = "achieved"
    ABANDONED = "abandoned"
