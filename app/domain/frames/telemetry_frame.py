from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta

from app.domain import measurements as m
from app.domain.frames.coordinates import Coordinates
from app.domain.measurements import Aspect, Measure
from app.domain.value_objects import (
    AlertState,
    ChannelReading,
    Condition,
    DeviceId,
    GasChannel,
    SignatureFlags,
)

_SECONDS_PER_MINUTE = 60.0


@dataclass(frozen=True, slots=True)
class TelemetryFrame:
    version: int
    seq: int
    measured_at: datetime
    state: AlertState
    conditions: frozenset[Condition] = frozenset()
    hw_id: DeviceId | None = None
    latched: bool = False
    values: dict[Measure, float] = field(default_factory=dict)
    signature: SignatureFlags | None = None
    batt_mv: int | None = None
    water: bool | None = None
    location: Coordinates | None = None

    def __post_init__(self) -> None:
        if self.measured_at.tzinfo is None:
            raise ValueError("measured_at은 timezone-aware여야 한다")
        m.validate(self.values)

    def value(self, measure: Measure) -> float | None:
        return self.values.get(measure)

    def with_slopes_since(
        self, previous: TelemetryFrame | None, *, within: timedelta
    ) -> TelemetryFrame:
        """직전 관측과의 변화율을 채운 프레임을 돌려준다. 단위는 분당이다.

        노드는 기울기를 보내지 않는다. 와이어에 자리가 없고, 노드가 1Hz 링버퍼로
        회귀해 얻는 기울기는 그 창 안에서만 뜻이 있어 전송 간격으로 옮길 수 없다.
        서버가 말할 수 있는 것은 연속한 두 관측 사이의 평균 변화율뿐이다 — 같은
        이름을 쓰지만 노드의 signature와 다른 값이고, 전송 간격이 굵을수록 무뎌진다.

        직전 관측이 `within`보다 오래됐으면 채우지 않는다. 그 사이 기기가 무엇을
        했는지 모르는 채로 두 점을 이으면, 변화율이 아니라 두 점의 차이를 시간으로
        나눈 숫자가 된다.

        노드가 이미 보낸 기울기는 건드리지 않는다. 서버가 채우는 것은 빈자리뿐이다.
        """
        derived = self._slopes_since(previous, within=within)
        if not derived:
            return self
        return replace(self, values={**self.values, **derived})

    def channel(self, channel: GasChannel) -> ChannelReading | None:
        slots = m.channel_measures(channel)
        deviation = self.values.get(slots[Aspect.DEVIATION])
        slope = self.values.get(slots[Aspect.SLOPE])
        if deviation is None and slope is None:
            return None
        return ChannelReading(channel=channel, deviation=deviation, slope=slope)

    def _slopes_since(
        self, previous: TelemetryFrame | None, *, within: timedelta
    ) -> dict[Measure, float]:
        if previous is None:
            return {}
        elapsed = self.measured_at - previous.measured_at
        if not timedelta(0) < elapsed <= within:
            return {}
        minutes = elapsed.total_seconds() / _SECONDS_PER_MINUTE
        return {
            slope: (now - before) / minutes
            for deviation, slope in m.SLOPE_BY_DEVIATION.items()
            if slope not in self.values
            and (now := self.values.get(deviation)) is not None
            and (before := previous.values.get(deviation)) is not None
        }
