from __future__ import annotations

from enum import StrEnum


class Condition(StrEnum):
    CO_RISE = "CO_RISE"
    H2_RISE = "H2_RISE"
    VOC_RISE = "VOC_RISE"
    PRESSURE_RISE = "PRESSURE_RISE"
    WATER = "WATER"
    SENSOR_FAULT = "SENSOR_FAULT"
