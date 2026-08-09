"""경보 저장소 통합 테스트."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain.value_objects import AlertState
from app.infrastructure.db.repositories.alerts import SqlAlchemyAlertRepository
from tests.builders import an_alert


class TestActiveAlerts:
    def test_acknowledged_alerts_are_excluded(
        self, alerts: SqlAlchemyAlertRepository, device_id: int, now: datetime
    ) -> None:
        open_alert = alerts.add(an_alert(now, device_id=device_id))
        closed = alerts.add(
            an_alert(now - timedelta(hours=1), device_id=device_id, to_state=AlertState.WATCH)
        )
        closed.acknowledge(at=now)
        alerts.save(closed)

        active = alerts.list_active()

        assert [a.id for a in active] == [open_alert.id]


class TestAcknowledge:
    def test_acknowledge_persists(
        self, alerts: SqlAlchemyAlertRepository, device_id: int, now: datetime
    ) -> None:
        alert = alerts.add(an_alert(now, device_id=device_id, from_state=AlertState.WATCH))
        alert.acknowledge(at=now + timedelta(minutes=3), note="현장 확인")
        alerts.save(alert)

        reloaded = alerts.get(alert.id or 0)

        assert reloaded is not None
        assert reloaded.is_active is False
        assert reloaded.acknowledged_note == "현장 확인"
        assert reloaded.acknowledged_at == (now + timedelta(minutes=3)).astimezone(UTC)
