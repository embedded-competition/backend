"""앱 spec §⑥ GET /devices/{id}/events — 기록 탭."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.infrastructure.db.repositories.events import SqlAlchemyEventRepository
from tests.builders import an_event
from tests.integration.api.client import RegisteredDevice


class TestEventList:
    async def test_returns_events_since(
        self, device: RegisteredDevice, session: Session, device_id: int, now: datetime
    ) -> None:
        SqlAlchemyEventRepository(session).add(an_event(now, device_id=device_id))
        session.commit()

        payload = (
            await device.get("events", params={"since": (now - timedelta(hours=1)).isoformat()})
        ).json()

        assert len(payload["items"]) == 1
        assert payload["items"][0]["kind"] == "suppressed"
        assert payload["items"][0]["id"].startswith("evt_")
