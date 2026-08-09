"""푸시 알림 문구. 서버가 소유한다 — 앱에 박으면 수정마다 스토어 심사."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.alerting import Alert
from app.domain.device import Device
from app.domain.value_objects import AlertState


@dataclass(frozen=True, slots=True)
class PushMessage:
    title: str
    body: str
    data: dict[str, str]


_TITLE = {
    AlertState.ALARM: "화재 발생 직전이에요",
    AlertState.WATCH: "이상 징후가 감지됐어요",
    AlertState.FAULT: "센서 점검이 필요해요",
}
_BODY = {
    AlertState.ALARM: "즉시 확인하세요",
    AlertState.WATCH: "앱에서 상태를 확인해 주세요",
    AlertState.FAULT: "감지가 멈춰 있어 확인이 필요합니다",
}


def build(alert: Alert, device: Device) -> PushMessage:
    """상세 수치는 담지 않는다 — 앱이 API로 조회한다."""
    return PushMessage(
        title=_TITLE.get(alert.to_state, "상태가 변경됐어요"),
        body=_BODY.get(alert.to_state, f"{device.label} 상태를 확인해 주세요"),
        # 딥링크로 상세 화면에 가도록 식별자를 싣는다
        data={
            "deviceId": device.public_id,
            "state": alert.to_state.value,
            "alertId": str(alert.id or ""),
        },
    )
