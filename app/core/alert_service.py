"""경보 해제 유스케이스.

앱은 해제 **요청**만 보낸다. 승인 여부는 서버 내부 규칙이고 사유를 앱에 내려주지
않는다 (앱 spec O8). 문구 생성은 descriptions.py.
"""

from __future__ import annotations

from app.core.descriptions import describe_release
from app.domain.exceptions import ReleaseNotAllowed
from app.domain.models import Alert, Device, Event
from app.domain.ports import Clock
from app.domain.repository import AlertRepository, EventRepository
from app.domain.value_objects import AlertState, EventKind


class AlertService:
    def __init__(self, *, alerts: AlertRepository, events: EventRepository, clock: Clock) -> None:
        self._alerts = alerts
        self._events = events
        self._clock = clock

    def active_for(self, device: Device) -> list[Alert]:
        return [a for a in self._alerts.list_active() if a.device_id == device.id]

    def request_release(self, device: Device, note: str | None = None) -> Alert:
        """해제 승인 규칙 (내부): 활성 ALARM 하나만 대상이다.

        없으면 거절한다 — 앱에는 `not_allowed`로만 응답하고 "왜"는 내려주지 않는다.
        """
        target = self._release_target(device)
        if target is None:
            raise ReleaseNotAllowed("해제할 활성 경보가 없다")

        now = self._clock.now()
        target.acknowledge(at=now, note=note)
        saved = self._alerts.save(target)
        self._events.add(
            Event(
                device_id=device.id or 0,
                alert_id=saved.id,
                kind=EventKind.ACTION,
                occurred_at=now,
                description=describe_release(note),
            )
        )
        return saved

    def _release_target(self, device: Device) -> Alert | None:
        candidates = [
            alert for alert in self.active_for(device) if alert.to_state is AlertState.ALARM
        ]
        return max(candidates, key=lambda a: a.occurred_at) if candidates else None
