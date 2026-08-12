from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.domain.module_health import BatteryLevel, LinkQuality, SensorCheck


@dataclass(frozen=True, slots=True)
class DeviceProfile:
    """기기가 무엇이고 그 모듈이 멀쩡한가. 설정 화면 한 번에 필요한 전부다.

    측정값은 여기 없다 — 텔레메트리는 초 단위로 바뀌고 이쪽은 거의 안 바뀐다.
    같이 담으면 안 바뀌는 것이 바뀌는 것의 주기를 따라간다.
    """

    mac: str
    label: str
    parking_slot: str | None = None
    battery: BatteryLevel | None = None
    """노드가 아직 전압을 보내지 않아 항상 None이다 — 프레임 v2의 power 블록(bit2) 대기.

    전압이 와도 곧바로 퍼센트가 되지는 않는다. 리튬 셀의 전압-잔량 곡선은 평평한
    구간이 길어 선형 변환하면 90%와 40%가 같은 전압으로 보인다. 셀 사양이 정해져야
    곡선을 쓸 수 있다.
    """
    link: LinkQuality | None = None
    sensor_check: SensorCheck | None = None
    last_seen_at: datetime | None = None
