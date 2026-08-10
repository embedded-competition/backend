from __future__ import annotations

import time
from typing import Any, Protocol

_HOLD_LOW_S = 0.001
_SETTLE_S = 0.005


class ResetPin(Protocol):
    def pulse(self) -> None: ...

    def close(self) -> None: ...


class GpioResetPin:
    def __init__(self, gpio: int) -> None:
        from gpiozero import OutputDevice

        self._pin: Any = OutputDevice(gpio, active_high=False, initial_value=False)

    def pulse(self) -> None:
        self._pin.on()
        time.sleep(_HOLD_LOW_S)
        self._pin.off()
        time.sleep(_SETTLE_S)

    def close(self) -> None:
        self._pin.close()
