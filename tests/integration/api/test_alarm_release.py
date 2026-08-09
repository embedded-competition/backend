"""앱 spec §⑤ POST /devices/{id}/alarm/release — 경보 해제."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.domain.value_objects import AlertState, EventKind
from app.infrastructure.db.repositories.alerts import SqlAlchemyAlertRepository
from app.infrastructure.db.repositories.events import SqlAlchemyEventRepository
from tests.builders import an_alert
from tests.integration.api.client import RegisteredDevice


class TestWithoutActiveAlarm:
    async def test_is_forbidden(self, device: RegisteredDevice) -> None:
        response = await device.post("alarm/release", json={})

        assert response.status_code == 403
        # 사유는 앱에 내려주지 않는다 (앱 spec O8)
        assert response.json()["error"] == "not_allowed"


class TestWithActiveAlarm:
    async def test_acknowledges_alarm(
        self, device: RegisteredDevice, session: Session, device_id: int, now: datetime
    ) -> None:
        alerts = SqlAlchemyAlertRepository(session)
        alerts.add(an_alert(now, device_id=device_id, from_state=AlertState.WATCH))
        session.commit()

        response = await device.post("alarm/release", json={"note": "현장 확인 완료"})

        assert response.status_code == 200
        assert response.json() == {"released": True}
        assert alerts.list_active() == []

    async def test_is_recorded_as_event(
        self, device: RegisteredDevice, session: Session, device_id: int, now: datetime
    ) -> None:
        SqlAlchemyAlertRepository(session).add(an_alert(now, device_id=device_id))
        session.commit()

        await device.post("alarm/release", json={})
        session.rollback()  # 읽기 트랜잭션 스냅샷을 끊어야 새 커밋이 보인다

        # 서버는 SystemClock으로 기록한다 — fixture 시각 기준 창을 쓰면 어긋난다.
        events = SqlAlchemyEventRepository(session).list_since(
            device_id, since=datetime(2020, 1, 1, tzinfo=UTC), limit=10
        )
        assert [e.kind for e in events] == [EventKind.ACTION]
        assert "경보 해제" in events[0].description
