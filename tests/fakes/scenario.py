from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.frames import Coordinates, TelemetryFrame
from app.domain.measurements import Measure
from app.domain.value_objects import AlertState, DeviceId
from app.infrastructure.lora.frame import ABSENT_SEQ, WIRE_FORMAT_ID

_SEOUL = Coordinates(lat=37.5573, lon=127.0329)


@dataclass(frozen=True, slots=True)
class ScenarioStep:
    """레벨은 노드가 보내는 그대로의 0~1000 정규화 값이다."""

    mq7: int
    mq8: int
    pressure: int
    water: int
    voc: int


DEFAULT_SCENARIO: tuple[ScenarioStep, ...] = (
    ScenarioStep(mq7=80, mq8=90, pressure=110, water=30, voc=120),
    ScenarioStep(mq7=95, mq8=110, pressure=120, water=32, voc=180),
    ScenarioStep(mq7=140, mq8=210, pressure=160, water=35, voc=430),
    ScenarioStep(mq7=180, mq8=340, pressure=190, water=38, voc=610),
    ScenarioStep(mq7=260, mq8=520, pressure=240, water=40, voc=880),
    ScenarioStep(mq7=130, mq8=180, pressure=150, water=33, voc=310),
)


class ScenarioFrameFactory:
    def __init__(
        self,
        hw_id: str,
        *,
        scenario: tuple[ScenarioStep, ...] = DEFAULT_SCENARIO,
        location: Coordinates | None = _SEOUL,
    ) -> None:
        self._hw_id = DeviceId(hw_id)
        self._scenario = scenario
        self._location = location

    def __len__(self) -> int:
        return len(self._scenario)

    def build(self, step: int, *, at: datetime | None = None) -> TelemetryFrame:
        """step은 시나리오 위치를 고르는 데만 쓴다 — 노드는 seq를 보내지 않는다."""
        levels = self._scenario[step % len(self._scenario)]
        return TelemetryFrame(
            version=WIRE_FORMAT_ID,
            hw_id=self._hw_id,
            seq=ABSENT_SEQ,
            measured_at=at or datetime.now(UTC),
            state=AlertState.NORMAL,
            values={
                Measure.CO_DEV: float(levels.mq7),
                Measure.H2_DEV: float(levels.mq8),
                Measure.PRESSURE_DEV: float(levels.pressure),
                Measure.WATER_LEVEL: float(levels.water),
                Measure.VOC_DEV: float(levels.voc),
            },
            location=self._location,
        )
