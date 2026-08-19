from __future__ import annotations

from enum import StrEnum


class Sensor(StrEnum):
    GAS = "gas"
    H2 = "h2"
    CO = "co"
    PRESSURE = "pressure"
    TEMP = "temp"
    RH = "rh"
