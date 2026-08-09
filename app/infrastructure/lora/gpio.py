"""SX1276 하드웨어 리셋 핀.

`gpiozero` import가 이 파일 밖으로 나가지 않는다. Mac·CI에는 GPIO가 없으므로
지연 import로 모듈 로드 자체는 어디서든 되게 한다 (spi.py와 같은 이유).
"""

from __future__ import annotations

import time
from typing import Any, Protocol

# 데이터시트 7.2.2 — NRESET을 100µs 이상 낮게 유지한 뒤 5ms 대기해야 칩이 선다.
_HOLD_LOW_S = 0.001
_SETTLE_S = 0.005


class ResetPin(Protocol):
    """리셋 신호 1회. 테스트는 이 Protocol의 fake를 주입한다."""

    def pulse(self) -> None: ...

    def close(self) -> None: ...


class GpioResetPin:
    """NRESET은 active-low라 초기값을 high로 두어야 부팅 중 리셋이 걸리지 않는다."""

    def __init__(self, gpio: int) -> None:
        # PLC0415 noqa 근거: gpiozero는 Pi 전용이라 최상위 import하면 Mac·CI에서
        # 모듈 로드 자체가 실패한다. 계층 회피가 아니라 플랫폼 격리다.
        from gpiozero import OutputDevice  # noqa: PLC0415

        self._pin: Any = OutputDevice(gpio, active_high=False, initial_value=False)

    def pulse(self) -> None:
        self._pin.on()
        time.sleep(_HOLD_LOW_S)
        self._pin.off()
        time.sleep(_SETTLE_S)

    def close(self) -> None:
        self._pin.close()
