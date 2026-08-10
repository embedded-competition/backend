from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SignatureFlags:
    rise: bool
    hold: bool
    no_recover: bool
    hold_s: int
