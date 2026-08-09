"""데모 시나리오 — 합성 프레임 생성. 방출 방식(주기·루프)은 모른다.

하드웨어 없이 앱 전 화면을 검증하기 위한 데이터 소스다.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.frames import Coordinates, TelemetryFrame
from app.domain.measurements import Measure
from app.domain.value_objects import AlertState, DeviceId, SignatureFlags
from app.infrastructure.lora.codec import FRAME_VERSION


@dataclass(frozen=True, slots=True)
class ScenarioStep:
    state: AlertState
    voc_dev: float
    voc_slope: float


# NORMAL 유지 → WATCH 승격 → ALARM 승격 → latch 유지
DEFAULT_SCENARIO: tuple[ScenarioStep, ...] = (
    ScenarioStep(AlertState.NORMAL, 0.2, 0.1),
    ScenarioStep(AlertState.NORMAL, 0.4, 0.3),
    ScenarioStep(AlertState.WATCH, 2.6, 2.4),
    ScenarioStep(AlertState.WATCH, 3.4, 2.8),
    ScenarioStep(AlertState.ALARM, 6.8, 7.2),
    ScenarioStep(AlertState.ALARM, 7.4, 5.1),
)


class ScenarioFrameFactory:
    """시나리오 스텝 → TelemetryFrame."""

    def __init__(
        self,
        hw_id: str,
        *,
        scenario: tuple[ScenarioStep, ...] = DEFAULT_SCENARIO,
        with_gps: bool = True,
    ) -> None:
        self._hw_id = DeviceId(hw_id)
        self._scenario = scenario
        self._with_gps = with_gps

    def __len__(self) -> int:
        return len(self._scenario)

    def build(self, seq: int, *, at: datetime | None = None) -> TelemetryFrame:
        step = self._scenario[seq % len(self._scenario)]
        promoted = step.state in (AlertState.WATCH, AlertState.ALARM)
        return TelemetryFrame(
            version=FRAME_VERSION,
            hw_id=self._hw_id,
            seq=seq,
            measured_at=at or datetime.now(UTC),
            state=step.state,
            latched=step.state is AlertState.ALARM,
            batt_mv=3960 - (seq % 40),
            values={
                Measure.VOC_DEV: step.voc_dev,
                Measure.VOC_SLOPE: step.voc_slope,
                Measure.H2_DEV: round(step.voc_dev * 0.4, 2),
                Measure.H2_SLOPE: round(step.voc_slope * 0.3, 2),
                Measure.TEMP_C: round(24.0 + step.voc_dev * 0.6, 2),
                Measure.HUMIDITY_PCT: round(41.0 + math.sin(seq / 5) * 3, 2),
                Measure.D_RH_DT: 0.2,
            },
            signature=SignatureFlags(
                rise=promoted,
                hold=step.state is AlertState.ALARM,
                no_recover=promoted,
                hold_s=32 if step.state is AlertState.ALARM else 0,
            ),
            water=False,
            location=Coordinates(lat=37.5573, lon=127.0329) if self._with_gps else None,
        )
