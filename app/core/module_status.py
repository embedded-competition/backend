from __future__ import annotations

from dataclasses import dataclass

from app.domain.module_health import BatteryLevel, LinkQuality, SensorCheck


@dataclass(frozen=True, slots=True)
class ModuleStatus:
    """감지 모듈이 스스로에 대해 답하는 것. 측정값이 무엇을 가리키는가와 다른 축이다.

    셋 다 판정 결과다. 근거가 된 전압·dBm·마지막 수신 시각은 담지 않는다 —
    내보내는 순간 앱이 그 값으로 다시 판정할 수 있게 되고, 그러면 임계가 두 곳에
    생긴다.
    """

    battery: BatteryLevel | None = None
    """노드가 아직 전압을 보내지 않아 항상 None이다 — 프레임 v2의 power 블록(bit2) 대기.

    전압이 와도 곧바로 퍼센트가 되지는 않는다. 리튬 셀의 전압-잔량 곡선은 평평한
    구간이 길어 선형 변환하면 90%와 40%가 같은 전압으로 보인다. 셀 사양이 정해져야
    곡선을 쓸 수 있다.
    """

    link: LinkQuality | None = None
    sensor_check: SensorCheck | None = None
