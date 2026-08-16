"""Enum types for the Tasks domain.

`StateMachines.md §3` defines the full lifecycle
`pending → claimed → in_progress → blocked → done | failed`, plus a retry
path back to `pending`. Per the M5 Step 3 plan's §0.1 cascading-
consequence analysis: only `pending` is reachable via any M5 endpoint —
`claimed`/`in_progress`/`blocked`/`done`/`failed` exist here for forward
compatibility only, never written by this checkpoint's code (`/claim` is
deferred pending machine identity, which transitively makes every later
state unreachable too).

`blocked_reason`'s three values are locked (decision A3), but — like the
statuses above — dormant: `blocked` itself is unreachable in M5, so
nothing ever writes `blocked_reason` either.
"""

from __future__ import annotations

import enum


class TaskStatus(enum.StrEnum):
    PENDING = "pending"
    CLAIMED = "claimed"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"
    FAILED = "failed"


class TaskBlockedReason(enum.StrEnum):
    AWAITING_DEPENDENCY = "awaiting_dependency"
    AWAITING_APPROVAL = "awaiting_approval"
    AWAITING_INPUT = "awaiting_input"
