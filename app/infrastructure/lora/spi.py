"""SPI 트랜스포트. 레지스터 읽기·쓰기만 안다 — 칩 의미는 모른다.

`spidev` import가 이 파일 밖으로 나가지 않는다. Mac·CI에는 SPI가 없으므로
지연 import로 모듈 로드 자체는 어디서든 되게 한다.
"""

from __future__ import annotations

from typing import Any, Protocol


class RegisterBus(Protocol):
    """레지스터 단위 접근. 테스트는 이 Protocol의 fake를 주입한다."""

    def read(self, register: int) -> int: ...

    def write(self, register: int, value: int) -> None: ...

    def close(self) -> None: ...


class SpiRegisterBus:
    def __init__(self, bus: int, device: int, *, max_speed_hz: int = 5_000_000) -> None:
        import spidev  # 지연 import — 하드웨어 없는 환경 보호

        self._spi: Any = spidev.SpiDev()
        self._spi.open(bus, device)
        self._spi.max_speed_hz = max_speed_hz
        self._spi.mode = 0

    def read(self, register: int) -> int:
        return int(self._spi.xfer2([register & 0x7F, 0x00])[1])

    def write(self, register: int, value: int) -> None:
        self._spi.xfer2([register | 0x80, value & 0xFF])

    def close(self) -> None:
        self._spi.close()
