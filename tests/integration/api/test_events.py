"""앱 spec §⑥ GET /devices/{id}/events — 기록 탭."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.infrastructure.db.repositories.events import SqlAlchemyEventRepository
from tests.builders import an_event
from tests.integration.api.client import RegisteredDevice


class TestEventList:
    async def test_returns_events_inside_the_period(
        self, device: RegisteredDevice, session: Session, device_id: int, now: datetime
    ) -> None:
        SqlAlchemyEventRepository(session).add(an_event(now, device_id=device_id))
        session.commit()

        payload = (
            await device.get(
                "events",
                params={
                    "since": (now - timedelta(hours=1)).isoformat(),
                    "until": (now + timedelta(hours=1)).isoformat(),
                },
            )
        ).json()

        assert len(payload["items"]) == 1
        assert payload["items"][0]["kind"] == "suppressed"
        assert payload["items"][0]["id"].startswith("evt_")

    async def test_event_outside_the_period_is_excluded(
        self, device: RegisteredDevice, session: Session, device_id: int, now: datetime
    ) -> None:
        SqlAlchemyEventRepository(session).add(an_event(now, device_id=device_id))
        session.commit()

        payload = (
            await device.get(
                "events",
                params={
                    "since": (now + timedelta(hours=1)).isoformat(),
                    "until": (now + timedelta(hours=2)).isoformat(),
                },
            )
        ).json()

        assert payload["items"] == []

    async def test_backwards_period_is_rejected(
        self, device: RegisteredDevice, now: datetime
    ) -> None:
        response = await device.get(
            "events",
            params={
                "since": now.isoformat(),
                "until": (now - timedelta(hours=1)).isoformat(),
            },
        )

        assert response.status_code == 422
        assert response.json()["error"] == "invalid_period"
