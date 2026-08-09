"""경보 해제 유스케이스.

앱은 해제 **요청**만 보낸다. 승인 여부는 서버 내부 규칙이고 사유를 앱에 내려주지
않는다 (앱 spec O8). 문구 생성은 descriptions.py.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.descriptions import describe_release
from app.domain.alerting import Alert, Event
from app.domain.device import Device
from app.domain.exceptions import ReleaseNotAllowed
from app.domain.ports.clock import Clock
from app.domain.value_objects import AlertState, EventKind
from app.infrastructure.db.repositories.alerts import SqlAlchemyAlertRepository
from app.infrastructure.db.repositories.events import SqlAlchemyEventRepository


@dataclass(frozen=True, slots=True)
class AlertService:
    """생성자 보일러플레이트는 dataclass가 만든다 (Lombok @RequiredArgsConstructor 대응)."""

    alerts: SqlAlchemyAlertRepository
    events: SqlAlchemyEventRepository
    clock: Clock

    def active_for(self, device: Device) -> list[Alert]:
        return self.alerts.list_active_for(device.key)

    def request_release(self, device: Device, note: str | None = None) -> Alert:
        """해제 승인 규칙 (내부): 활성 ALARM 하나만 대상이다.

        없으면 거절한다 — 앱에는 `not_allowed`로만 응답하고 "왜"는 내려주지 않는다.
        """
        target = self._release_target(device)
        if target is None:
            raise ReleaseNotAllowed("해제할 활성 경보가 없다")

        now = self.clock.now()
        target.acknowledge(at=now, note=note)
        saved = self.alerts.save(target)
        self.events.add(
            Event(
                device_id=device.key,
                alert_id=saved.key,
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
