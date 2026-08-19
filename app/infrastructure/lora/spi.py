from __future__ import annotations

from typing import Any, Protocol


class RegisterBus(Protocol):
    def read(self, register: int) -> int: ...

    def write(self, register: int, value: int) -> None: ...

    def close(self) -> None: ...


class SpiRegisterBus:
    def __init__(self, bus: int, device: int, *, max_speed_hz: int = 5_000_000) -> None:
        import spidev

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
