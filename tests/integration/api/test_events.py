"""앱 spec §⑥ GET /devices/{id}/events — 기록 탭."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.telemetry_service import _EVENT_LIMIT
from app.infrastructure.db.repositories.events import SqlAlchemyEventRepository
from tests.builders import an_event
from tests.integration.api.client import SeededDevice


class TestEventList:
    async def test_returns_events_inside_the_period(
        self, device: SeededDevice, session: Session, device_id: int, now: datetime
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
        assert payload["truncated"] is False

    async def test_truncation_is_signalled_not_silent(
        self, device: SeededDevice, session: Session, device_id: int, now: datetime
    ) -> None:
        """예전엔 200개에서 조용히 잘렸다 — 클라가 잘림 여부를 알 방법이 없었다."""
        events = SqlAlchemyEventRepository(session)
        for offset in range(_EVENT_LIMIT + 5):
            events.add(an_event(now + timedelta(seconds=offset), device_id=device_id))
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

        assert len(payload["items"]) == _EVENT_LIMIT
        assert payload["truncated"] is True

    async def test_event_outside_the_period_is_excluded(
        self, device: SeededDevice, session: Session, device_id: int, now: datetime
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

    async def test_backwards_period_is_rejected(self, device: SeededDevice, now: datetime) -> None:
        response = await device.get(
            "events",
            params={
                "since": now.isoformat(),
                "until": (now - timedelta(hours=1)).isoformat(),
            },
        )

        assert response.status_code == 422
        assert response.json()["error"] == "invalid_period"
