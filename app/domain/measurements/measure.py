from __future__ import annotations

from enum import StrEnum


class Measure(StrEnum):
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
    WATER_LEVEL = "water_level"
