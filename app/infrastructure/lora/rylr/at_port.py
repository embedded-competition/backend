from __future__ import annotations

from typing import Protocol


class AtPort(Protocol):
    def write_line(self, line: str) -> None: ...

    def read_line(self, timeout_s: float) -> str | None: ...

    def close(self) -> None: ...
