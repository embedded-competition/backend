from __future__ import annotations


class NotStored(RuntimeError):
    pass


def require_stored(identifier: int | None, name: str) -> int:
    if identifier is None:
        raise NotStored(f"{name}가 아직 저장되지 않았다 — 식별자가 없다")
    return identifier
