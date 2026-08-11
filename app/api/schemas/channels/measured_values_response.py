from __future__ import annotations

from typing import Annotated, Any, Protocol

from pydantic import Field

from app.api.schemas.base import ApiModel
from app.api.schemas.channels.gas_channel_response import GasChannelResponse
from app.domain.measurements import Aspect, Measure, channel_measures
from app.domain.value_objects import GasChannel


class MeasuredValues(Protocol):
    def value(self, measure: Measure) -> float | None: ...


class MeasuredValuesResponse(ApiModel):
    gas: GasChannelResponse
    h2: GasChannelResponse
    co: GasChannelResponse
    temp_c: Annotated[float | None, Field(examples=[26.1])] = None
    rh: Annotated[float | None, Field(examples=[43.4])] = None
    pres_dev: float | None = None

    @classmethod
    def fields_of(cls, values: MeasuredValues) -> dict[str, Any]:
        return {
            "gas": _channel(values, GasChannel.VOC),
            "h2": _channel(values, GasChannel.H2),
            "co": _channel(values, GasChannel.CO),
            "temp_c": values.value(Measure.TEMP_C),
            "rh": values.value(Measure.HUMIDITY_PCT),
            "pres_dev": values.value(Measure.PRESSURE_DEV),
        }


def _channel(values: MeasuredValues, channel: GasChannel) -> GasChannelResponse:
    slots = channel_measures(channel)
    return GasChannelResponse(
        dev_z=values.value(slots[Aspect.DEVIATION]),
        slope=values.value(slots[Aspect.SLOPE]),
    )
