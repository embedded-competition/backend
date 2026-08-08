"""디코딩된 텔레메트리 프레임.

무선 인코딩(오프셋·스케일·CRC)은 infrastructure가 알고, 이 타입은 "노드가 무엇을
보냈는가"만 표현한다. core가 infrastructure를 import하지 않도록 domain에 둔다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.value_objects import (
    AlertState,
    ChannelReading,
    DeviceId,
    SignatureFlags,
)


@dataclass(frozen=True, slots=True)
class TelemetryFrame:
    """프레임 1건. 아직 내부 device PK를 모른다 — hw_id로만 식별된다."""

    version: int
    hw_id: DeviceId
    seq: int
    measured_at: datetime
    state: AlertState
    latched: bool
    batt_mv: int | None = None
    channels: tuple[ChannelReading, ...] = ()
    signature: SignatureFlags | None = None
    temp_c: float | None = None
    humidity_pct: float | None = None
    d_rh_dt: float | None = None
    pressure_dev: float | None = None
    pressure_rate: float | None = None
    water: bool | None = None
    lat: float | None = None
    lon: float | None = None
