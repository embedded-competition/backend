"""측정 항목 SSOT.

센서 값을 필드마다 선언하면 채널 하나 추가에 11개 파일을 고쳐야 했다.
이 표 하나가 검증 범위·DB 컬럼명·와이어 순서·응답 그룹핑을 전부 규정한다.
항목 추가 = 아래 enum 1줄 + spec 1줄 + DB 컬럼 1개.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from app.domain.value_objects import GasChannel


class Aspect(StrEnum):
    """가스 채널이 갖는 두 관점 (gas-detection-algorithm-design.md)."""

    DEVIATION = "deviation"
    """baseline 대비 z-score."""
    SLOPE = "slope"
    """deviation 변화율 (z/min)."""


class Measure(StrEnum):
    """값은 DB 컬럼명과 같다 — 매핑 코드를 없애기 위한 의도적 결합."""

    VOC_DEV = "voc_dev"
    VOC_SLOPE = "voc_slope"
    H2_DEV = "h2_dev"
    H2_SLOPE = "h2_slope"
    CO_DEV = "co_dev"
    CO_SLOPE = "co_slope"
    TEMP_C = "temp_c"
    HUMIDITY_PCT = "humidity_pct"
    D_RH_DT = "d_rh_dt"
    PRESSURE_DEV = "pressure_dev"
    PRESSURE_RATE = "pressure_rate"


@dataclass(frozen=True, slots=True)
class MeasureSpec:
    unit: str
    minimum: float | None = None
    maximum: float | None = None
    channel: GasChannel | None = None
    aspect: Aspect | None = None


SPECS: dict[Measure, MeasureSpec] = {
    Measure.VOC_DEV: MeasureSpec("z", channel=GasChannel.VOC, aspect=Aspect.DEVIATION),
    Measure.VOC_SLOPE: MeasureSpec("z/min", channel=GasChannel.VOC, aspect=Aspect.SLOPE),
    Measure.H2_DEV: MeasureSpec("z", channel=GasChannel.H2, aspect=Aspect.DEVIATION),
    Measure.H2_SLOPE: MeasureSpec("z/min", channel=GasChannel.H2, aspect=Aspect.SLOPE),
    Measure.CO_DEV: MeasureSpec("z", channel=GasChannel.CO, aspect=Aspect.DEVIATION),
    Measure.CO_SLOPE: MeasureSpec("z/min", channel=GasChannel.CO, aspect=Aspect.SLOPE),
    Measure.TEMP_C: MeasureSpec("°C", minimum=-40.0, maximum=125.0),
    Measure.HUMIDITY_PCT: MeasureSpec("%RH", minimum=0.0, maximum=100.0),
    Measure.D_RH_DT: MeasureSpec("%RH/min"),
    Measure.PRESSURE_DEV: MeasureSpec("z"),
    Measure.PRESSURE_RATE: MeasureSpec("z/min"),
}

# 와이어·DB 양쪽이 쓰는 고정 순서. 새 항목은 반드시 끝에 추가한다
# (중간 삽입은 프레임 오프셋을 밀어 노드 펌웨어와 어긋난다).
ORDER: tuple[Measure, ...] = tuple(SPECS)


def spec_of(measure: Measure) -> MeasureSpec:
    return SPECS[measure]


def channel_measures(channel: GasChannel) -> dict[Aspect, Measure]:
    """가스 채널 하나가 갖는 dev·slope 쌍."""
    return {
        spec.aspect: measure
        for measure, spec in SPECS.items()
        if spec.channel is channel and spec.aspect is not None
    }


def validate(values: dict[Measure, float]) -> None:
    """범위 검증을 한 곳에서. 필드마다 if를 늘어놓지 않는다."""
    for measure, value in values.items():
        spec = SPECS[measure]
        if spec.minimum is not None and value < spec.minimum:
            raise ValueError(f"{measure.value} 범위 이탈: {value} < {spec.minimum}")
        if spec.maximum is not None and value > spec.maximum:
            raise ValueError(f"{measure.value} 범위 이탈: {value} > {spec.maximum}")
