from __future__ import annotations

from dataclasses import dataclass

_HW_ID_MAX_LENGTH = 32


@dataclass(frozen=True, slots=True)
class DeviceId:
    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("device hw_id는 비어 있을 수 없다")
        if len(self.value) > _HW_ID_MAX_LENGTH:
            raise ValueError(f"device hw_id가 너무 길다: {len(self.value)}자")

    def __str__(self) -> str:
        return self.value
