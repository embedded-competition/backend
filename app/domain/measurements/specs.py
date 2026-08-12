from __future__ import annotations

from app.domain.measurements.aspect import Aspect
from app.domain.measurements.measure import Measure
from app.domain.measurements.measure_spec import MeasureSpec
from app.domain.measurements.sensor import Sensor
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

SLOPE_BY_DEVIATION: dict[Measure, Measure] = {
    Measure.VOC_DEV: Measure.VOC_SLOPE,
    Measure.H2_DEV: Measure.H2_SLOPE,
    Measure.CO_DEV: Measure.CO_SLOPE,
    Measure.PRESSURE_DEV: Measure.PRESSURE_RATE,
}

# 앱은 VOC 채널을 "gas"라 부른다 (앱 spec 정합화) — 여기서만 그 이름이 등장한다.
SENSOR_MEASURES: dict[Sensor, tuple[Measure, Measure | None]] = {
    Sensor.GAS: (Measure.VOC_DEV, Measure.VOC_SLOPE),
    Sensor.H2: (Measure.H2_DEV, Measure.H2_SLOPE),
    Sensor.CO: (Measure.CO_DEV, Measure.CO_SLOPE),
    Sensor.PRESSURE: (Measure.PRESSURE_DEV, Measure.PRESSURE_RATE),
    Sensor.TEMP: (Measure.TEMP_C, None),
    Sensor.RH: (Measure.HUMIDITY_PCT, None),
}


def channel_measures(channel: GasChannel) -> dict[Aspect, Measure]:
    return {
        spec.aspect: measure
        for measure, spec in SPECS.items()
        if spec.channel is channel and spec.aspect is not None
    }


def sensor_measures(sensor: Sensor) -> tuple[Measure, Measure | None]:
    return SENSOR_MEASURES[sensor]


def validate(values: dict[Measure, float]) -> None:
    for measure, value in values.items():
        spec = SPECS[measure]
        if spec.minimum is not None and value < spec.minimum:
            raise ValueError(f"{measure.value} 범위 이탈: {value} < {spec.minimum}")
        if spec.maximum is not None and value > spec.maximum:
            raise ValueError(f"{measure.value} 범위 이탈: {value} > {spec.maximum}")
