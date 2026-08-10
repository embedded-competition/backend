from __future__ import annotations

from app.domain.measurements.aspect import Aspect
from app.domain.measurements.measure import Measure
from app.domain.measurements.measure_spec import MeasureSpec
from app.domain.value_objects import GasChannel

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

ORDER: tuple[Measure, ...] = tuple(SPECS)


def channel_measures(channel: GasChannel) -> dict[Aspect, Measure]:
    return {
        spec.aspect: measure
        for measure, spec in SPECS.items()
        if spec.channel is channel and spec.aspect is not None
    }


def validate(values: dict[Measure, float]) -> None:
    for measure, value in values.items():
        spec = SPECS[measure]
        if spec.minimum is not None and value < spec.minimum:
            raise ValueError(f"{measure.value} 범위 이탈: {value} < {spec.minimum}")
        if spec.maximum is not None and value > spec.maximum:
            raise ValueError(f"{measure.value} 범위 이탈: {value} > {spec.maximum}")
