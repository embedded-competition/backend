from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PayloadEncoding = Literal["base64url", "hex", "text", "node_csv"]

_BANDWIDTH_CODES = {125_000: 7, 250_000: 8, 500_000: 9}
_LOWEST_CODING_RATE = 5


@dataclass(frozen=True, slots=True)
class RylrConfig:
    port: str
    baud: int
    address: int
    network_id: int
    frequency_hz: int
    spreading_factor: int
    bandwidth_hz: int
    coding_rate: int
    preamble_length: int
    payload: PayloadEncoding = "base64url"
    read_timeout_s: float = 1.0
    command_timeout_s: float = 2.0

    @property
    def bandwidth_code(self) -> int:
        code = _BANDWIDTH_CODES.get(self.bandwidth_hz)
        if code is None:
            supported = ", ".join(f"{hz // 1000}kHz" for hz in _BANDWIDTH_CODES)
            raise ValueError(
                f"RYLR이 지원하지 않는 대역폭: {self.bandwidth_hz}Hz — {supported}만 된다"
            )
        return code

    @property
    def coding_rate_code(self) -> int:
        return self.coding_rate - _LOWEST_CODING_RATE + 1

    @property
    def parameter_command(self) -> str:
        return (
            f"AT+PARAMETER={self.spreading_factor},{self.bandwidth_code},"
            f"{self.coding_rate_code},{self.preamble_length}"
        )
