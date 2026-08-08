"""경보 해제 유스케이스.

앱은 해제 **요청**만 보낸다. 승인 여부는 서버가 내부 규칙으로 판단하고
사유를 앱에 내려주지 않는다 (앱 spec O8).
"""

from __future__ import annotations

from app.domain.exceptions import ReleaseNotAllowed
from app.domain.models import Alert, Device, Event
from app.domain.ports import Clock
from app.domain.repository import AlertRepository, EventRepository
from app.domain.value_objects import AlertState, EventKind

_STATE_LABEL = {
    AlertState.WARMUP: "예열",
    AlertState.NORMAL: "정상",
    AlertState.WATCH: "주의",
    AlertState.ALARM: "경보",
    AlertState.FAULT: "고장",
}


def describe_transition(from_state: AlertState, to_state: AlertState) -> str:
    """기록 탭 문장. 서버가 생성한다 (앱 C5)."""
    return f"{_STATE_LABEL[from_state]} → {_STATE_LABEL[to_state]} 전환"


class AlertService:
    def __init__(
        self,
        *,
        alerts: AlertRepository,
        events: EventRepository,
        clock: Clock,
    ) -> None:
        self._alerts = alerts
        self._events = events
        self._clock = clock

    def active_for(self, device: Device) -> list[Alert]:
        return [a for a in self._alerts.list_active() if a.device_id == device.id]

    def request_release(self, device: Device, note: str | None = None) -> Alert:
        """해제 승인 규칙 (내부):

        해제 대상은 활성 ALARM 하나뿐이다. 없으면 거절한다 — 앱에는
        `not_allowed`로만 응답하고 "왜"는 내려주지 않는다.
        """
        candidates = [
            alert for alert in self.active_for(device) if alert.to_state is AlertState.ALARM
        ]
        if not candidates:
            raise ReleaseNotAllowed("해제할 활성 경보가 없다")

        target = max(candidates, key=lambda a: a.occurred_at)
        now = self._clock.now()
        target.acknowledge(at=now, note=note)
        saved = self._alerts.save(target)

        self._events.add(
            Event(
                device_id=device.id or 0,
                alert_id=saved.id,
                kind=EventKind.ACTION,
                occurred_at=now,
                description="사용자 요청으로 경보 해제됨" + (f" ({note})" if note else ""),
            )
        )
        return saved
