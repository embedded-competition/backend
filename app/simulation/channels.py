from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.domain.measurements import Measure
from app.domain.value_objects import Condition

LEVEL_MIN = 0.0
LEVEL_MAX = 1000.0


@dataclass(frozen=True, slots=True, order=True)
class Level:
    """노드가 보내는 0~1000 정규화 눈금 (docs/lora-frame.md).

    범위를 벗어난 값으로는 태어나지 못한다. 범위 밖을 접어 넣는 일은 `clamped`
    한 곳에서만 일어나므로, 어디서 잘렸는지 읽어서 알 수 있다.
    """

    value: float

    def __post_init__(self) -> None:
        if not LEVEL_MIN <= self.value <= LEVEL_MAX:
            raise ValueError(f"레벨이 {LEVEL_MIN}~{LEVEL_MAX} 밖이다: {self.value}")

    @classmethod
    def clamped(cls, value: float) -> Level:
        return cls(min(max(value, LEVEL_MIN), LEVEL_MAX))

    @property
    def is_saturated(self) -> bool:
        return self.value >= LEVEL_MAX

    def toward(self, other: Level, progress: float) -> Level:
        return Level.clamped(self.value + (other.value - self.value) * progress)


@dataclass(frozen=True, slots=True)
class ChannelSpec:
    """한 채널이 어느 눈금에서 무엇을 뜻하게 되는지.

    `alarm_at`이 없는 채널은 경보로 올라가지 않는다 — 침수는 화재 진행이 아니라
    다른 축이고, 그 축에는 경보 단계가 없다.
    """

    measure: Measure
    condition: Condition
    baseline: Level
    watch_at: Level
    alarm_at: Level | None

    def condition_of(self, level: Level) -> Condition | None:
        """포화는 위험이 아니라 불신이다 — 다른 원인과 섞지 않는다."""
        if level.is_saturated:
            return Condition.SENSOR_FAULT
        if level >= self.watch_at:
            return self.condition
        return None

    def alarms(self, level: Level) -> bool:
        if self.alarm_at is None or level.is_saturated:
            return False
        return level >= self.alarm_at


class NodeChannel(StrEnum):
    """노드가 실제로 보내는 다섯 채널. 앱 화면 축(`Sensor`)과 다른 목록이다 —
    노드는 침수를 보내고 온습도는 보내지 않는다."""

    CO = "co"
    H2 = "h2"
    VOC = "voc"
    PRESSURE = "pressure"
    WATER = "water"

    @property
    def spec(self) -> ChannelSpec:
        return _SPECS[self]


_SPECS: dict[NodeChannel, ChannelSpec] = {
    NodeChannel.CO: ChannelSpec(
        measure=Measure.CO_DEV,
        condition=Condition.CO_RISE,
        baseline=Level(80.0),
        watch_at=Level(400.0),
        alarm_at=Level(750.0),
    ),
    NodeChannel.H2: ChannelSpec(
        measure=Measure.H2_DEV,
        condition=Condition.H2_RISE,
        baseline=Level(90.0),
        watch_at=Level(400.0),
        alarm_at=Level(750.0),
    ),
    NodeChannel.VOC: ChannelSpec(
        measure=Measure.VOC_DEV,
        condition=Condition.VOC_RISE,
        baseline=Level(120.0),
        watch_at=Level(450.0),
        alarm_at=Level(800.0),
    ),
    NodeChannel.PRESSURE: ChannelSpec(
        measure=Measure.PRESSURE_DEV,
        condition=Condition.PRESSURE_RISE,
        baseline=Level(110.0),
        watch_at=Level(400.0),
        alarm_at=Level(780.0),
    ),
    NodeChannel.WATER: ChannelSpec(
        measure=Measure.WATER_LEVEL,
        condition=Condition.WATER,
        baseline=Level(30.0),
        watch_at=Level(300.0),
        alarm_at=None,
    ),
}
