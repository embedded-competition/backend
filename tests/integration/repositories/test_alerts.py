"""경보 저장소 통합 테스트."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.domain.value_objects import AlertState
from app.infrastructure.db.repositories.alerts import SqlAlchemyAlertRepository
from app.infrastructure.db.repositories.devices import SqlAlchemyDeviceRepository
from tests.builders import a_device, an_alert


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

        active = alerts.list_active_for(device_id)

        assert [a.id for a in active] == [open_alert.id]

    def test_other_devices_alerts_are_excluded(
        self,
        alerts: SqlAlchemyAlertRepository,
        devices: SqlAlchemyDeviceRepository,
        device_id: int,
        now: datetime,
    ) -> None:
        """전체를 읽어 파이썬에서 거르면 기기가 늘수록 읽는 양이 같이 는다."""
        neighbour = devices.save(
            a_device(public_id="dev_other", mac="AA:BB:CC:00:00:01", hw_id=None, registered_at=now)
        )
        mine = alerts.add(an_alert(now, device_id=device_id))
        alerts.add(an_alert(now, device_id=neighbour.key))

        assert [a.id for a in alerts.list_active_for(device_id)] == [mine.id]


class TestAcknowledge:
    def test_acknowledge_persists(
        self, alerts: SqlAlchemyAlertRepository, device_id: int, now: datetime
    ) -> None:
        alert = alerts.add(an_alert(now, device_id=device_id, from_state=AlertState.WATCH))
        alert.acknowledge(at=now + timedelta(minutes=3), note="현장 확인")
        alerts.save(alert)

        reloaded = alerts.get(alert.key)

        assert reloaded is not None
        assert reloaded.is_active is False
        assert reloaded.acknowledged_note == "현장 확인"
        assert reloaded.acknowledged_at == (now + timedelta(minutes=3)).astimezone(UTC)
