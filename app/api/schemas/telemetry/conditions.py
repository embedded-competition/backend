from __future__ import annotations

from app.domain.value_objects import Condition

_ORDER = tuple(Condition)


def ordered_conditions(conditions: frozenset[Condition]) -> list[Condition]:
    return [condition for condition in _ORDER if condition in conditions]
