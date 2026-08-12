"""감지 모듈이 스스로에 대해 답하는 것들.

측정값이 무엇을 가리키는가와 별개로, 모듈 자체가 멀쩡한지를 묻는 축이다.
앱 설정 화면이 이 셋을 나란히 보여준다 — 배터리·연결·센서.

임계는 전부 여기 있다. 앱이 dBm이나 mV를 받아 스스로 판정하면 서버와 어긋나고,
어긋난 줄도 모른다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from app.domain.value_objects import Condition


class LinkQuality(StrEnum):
    """연결 상태. 신호 세기보다 '지금 닿는가'가 먼저다."""

    OFFLINE = "OFFLINE"
    POOR = "POOR"
    FAIR = "FAIR"
    GOOD = "GOOD"

    @classmethod
    def of(
        cls,
        *,
        rssi: int | None,
        last_seen_at: datetime | None,
        now: datetime,
        offline_after: timedelta,
    ) -> LinkQuality | None:
        """한 번도 못 받았으면 None이다 — 끊긴 것과 아직 안 온 것은 다르다."""
        if last_seen_at is None:
            return None
        if now - last_seen_at > offline_after:
            return cls.OFFLINE
        if rssi is None:
            return cls.FAIR
        if rssi >= _GOOD_DBM:
            return cls.GOOD
        if rssi >= _FAIR_DBM:
            return cls.FAIR
        return cls.POOR


_GOOD_DBM = -100
_FAIR_DBM = -115
"""SF9/BW125 수신 감도가 약 -129dBm이다. -115를 넘어서면 여유가 한 자릿수 dB로
줄어 비 한 번에 끊긴다. 끊기고 나서 알리면 늦으므로 그 전에 낮춰 부른다."""


_EMPTY = 0
_FULL = 100


class SensorCheck(StrEnum):
    OK = "OK"
    FAULT = "FAULT"

    @classmethod
    def of(cls, conditions: frozenset[Condition] | None) -> SensorCheck | None:
        if conditions is None:
            return None
        return cls.FAULT if Condition.SENSOR_FAULT in conditions else cls.OK


@dataclass(frozen=True, slots=True)
class BatteryLevel:
    """남은 양과 남은 날. 앱은 이 둘로 문장을 만든다.

    "78% · 약 40일 남음" 같은 문장을 서버가 만들지 않는다. 단위와 어투가 바뀔 때
    서버를 배포해야 하는 것은 표현을 잘못 둔 것이다.
    """

    percent: int
    days_left: int | None = None

    def __post_init__(self) -> None:
        if not _EMPTY <= self.percent <= _FULL:
            raise ValueError(f"percent는 {_EMPTY}~{_FULL}이어야 한다: {self.percent}")
        if self.days_left is not None and self.days_left < 0:
            raise ValueError(f"days_left는 음수일 수 없다: {self.days_left}")
