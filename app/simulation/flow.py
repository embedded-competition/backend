from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from app.domain.timestamps import require_aware
from app.simulation.channels import Level, NodeChannel


class Direction(StrEnum):
    RISE = "rise"
    FALL = "fall"

    def applied(self, level: Level, amount: float) -> Level:
        step = amount if self is Direction.RISE else -amount
        return Level.clamped(level.value + step)


@dataclass(frozen=True, slots=True)
class FlowCommand:
    """한 채널을 어느 쪽으로 얼마나, 몇 초에 걸쳐 옮길지."""

    direction: Direction
    amount: float
    over_seconds: float

    def __post_init__(self) -> None:
        if self.amount <= 0:
            raise ValueError(f"변화량은 양수여야 한다: {self.amount}")
        if self.over_seconds < 0:
            raise ValueError(f"소요 시간은 음수일 수 없다: {self.over_seconds}")

    @property
    def is_immediate(self) -> bool:
        return self.over_seconds == 0

    def target_from(self, origin: Level) -> Level:
        return self.direction.applied(origin, self.amount)


@dataclass(frozen=True, slots=True)
class Ramp:
    """시작 레벨에서 목표 레벨까지 정해진 시간 동안 선형으로 옮긴다."""

    origin: Level
    target: Level
    started_at: datetime
    seconds: float

    def __post_init__(self) -> None:
        if self.seconds <= 0:
            raise ValueError(f"램프 길이는 양수여야 한다: {self.seconds}")
        require_aware(self.started_at, "started_at")

    def level_at(self, now: datetime) -> Level:
        return self.origin.toward(self.target, self._progress(now))

    def finished_by(self, now: datetime) -> bool:
        return self._progress(now) >= 1.0

    def remaining_seconds(self, now: datetime) -> float:
        return self.seconds * (1.0 - self._progress(now))

    def _progress(self, now: datetime) -> float:
        elapsed = (now - self.started_at).total_seconds()
        return min(max(elapsed / self.seconds, 0.0), 1.0)


@dataclass(slots=True)
class SensorFlow:
    """한 채널의 현재 레벨과 진행 중인 흐름."""

    channel: NodeChannel
    level: Level
    ramp: Ramp | None = None

    @classmethod
    def at_baseline(cls, channel: NodeChannel) -> SensorFlow:
        return cls(channel=channel, level=channel.spec.baseline)

    def steer(self, command: FlowCommand, *, at: datetime) -> None:
        """진행 중인 흐름이 있으면 지금 위치에서 다시 출발한다."""
        origin = self.level_at(at)
        target = command.target_from(origin)
        if command.is_immediate:
            self.level = target
            self.ramp = None
            return
        self.level = origin
        self.ramp = Ramp(origin=origin, target=target, started_at=at, seconds=command.over_seconds)

    def level_at(self, now: datetime) -> Level:
        return self.level if self.ramp is None else self.ramp.level_at(now)

    def settle(self, now: datetime) -> Level:
        """이번 틱의 레벨을 확정한다. 끝난 램프는 여기서 사라진다."""
        self.level = self.level_at(now)
        if self.ramp is not None and self.ramp.finished_by(now):
            self.ramp = None
        return self.level

    def reset(self) -> None:
        self.level = self.channel.spec.baseline
        self.ramp = None

    @property
    def target(self) -> Level | None:
        return self.ramp.target if self.ramp is not None else None

    def remaining_seconds(self, now: datetime) -> float | None:
        return self.ramp.remaining_seconds(now) if self.ramp is not None else None
