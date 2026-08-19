from __future__ import annotations

from enum import StrEnum


class EventKind(StrEnum):
    STATE_CHANGE = "state_change"
    ACTION = "action"
    SUPPRESSED = "suppressed"
