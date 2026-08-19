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
    alerts: SqlAlchemyAlertRepository
    events: SqlAlchemyEventRepository
    clock: Clock

    def active_for(self, device: Device) -> list[Alert]:
        return self.alerts.list_active_for(device.key)

    def request_release(self, device: Device, note: str | None = None) -> Alert:
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
