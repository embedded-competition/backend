"""앱 사용 순서(api-spec.md §API 사용 순서) 전체 흐름 검증.

등록 → 푸시토큰 → 폴링 → 경보 해제.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from app.domain.models import Alert, Event, Reading
from app.domain.value_objects import (
    AlertState,
    ChannelReading,
    EventKind,
    GasChannel,
    SignatureFlags,
)
from app.infrastructure.db.repositories import (
    SqlAlchemyAlertRepository,
    SqlAlchemyEventRepository,
    SqlAlchemyReadingRepository,
)

MAC = "AA:BB:CC:DD:EE:FF"


async def _register(client: AsyncClient, mac: str = MAC) -> dict[str, str]:
    response = await client.post("/devices", json={"mac": mac})
    assert response.status_code == 201, response.text
    return dict(response.json())


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class TestRegistration:
    async def test_register_returns_id_and_token(self, client: AsyncClient) -> None:
        body = await _register(client)

        assert body["deviceId"].startswith("dev_")
        assert body["deviceToken"].startswith("dtk_")

    async def test_duplicate_mac_is_rejected(self, client: AsyncClient) -> None:
        await _register(client)

        response = await client.post("/devices", json={"mac": MAC})

        assert response.status_code == 409
        assert response.json()["error"] == "already_paired"

    async def test_mac_is_normalized_before_duplicate_check(self, client: AsyncClient) -> None:
        """구분자·대소문자가 달라도 같은 기기다."""
        await _register(client)

        response = await client.post("/devices", json={"mac": "aa-bb-cc-dd-ee-ff"})

        assert response.status_code == 409

    async def test_malformed_mac_is_rejected(self, client: AsyncClient) -> None:
        response = await client.post("/devices", json={"mac": "not-a-mac-at-all"})

        assert response.status_code == 422
        assert response.json()["error"] == "invalid_mac"


class TestAuthentication:
    async def test_missing_header_is_unauthorized(self, client: AsyncClient) -> None:
        body = await _register(client)

        response = await client.get(f"/devices/{body['deviceId']}/telemetry/latest")

        assert response.status_code == 401
        assert response.json()["error"] == "unauthorized"

    async def test_bad_token_is_unauthorized(self, client: AsyncClient) -> None:
        body = await _register(client)

        response = await client.get(
            f"/devices/{body['deviceId']}/telemetry/latest",
            headers=_auth("dtk_wrong"),
        )

        assert response.status_code == 401

    async def test_other_device_id_is_not_found(self, client: AsyncClient) -> None:
        """다른 기기 id를 넣으면 404 — 403이면 그 기기의 존재가 새어나간다."""
        mine = await _register(client)
        other = await _register(client, "11:22:33:44:55:66")

        response = await client.get(
            f"/devices/{other['deviceId']}/telemetry/latest",
            headers=_auth(mine["deviceToken"]),
        )

        assert response.status_code == 404
        assert response.json()["error"] == "device_not_found"

    async def test_error_body_carries_request_id(self, client: AsyncClient) -> None:
        response = await client.get("/devices/dev_nope/telemetry/latest")

        assert response.json()["requestId"]


class TestPushToken:
    async def test_register_push_token(self, client: AsyncClient) -> None:
        body = await _register(client)

        response = await client.post(
            f"/devices/{body['deviceId']}/push-token",
            headers=_auth(body["deviceToken"]),
            json={"token": "ExponentPushToken[abc123]"},
        )

        assert response.status_code == 200
        assert response.json() == {"registered": True}

    async def test_reregistration_is_idempotent(self, client: AsyncClient) -> None:
        body = await _register(client)
        payload = {"token": "ExponentPushToken[abc123]"}
        headers = _auth(body["deviceToken"])

        first = await client.post(
            f"/devices/{body['deviceId']}/push-token", headers=headers, json=payload
        )
        second = await client.post(
            f"/devices/{body['deviceId']}/push-token", headers=headers, json=payload
        )

        assert first.status_code == second.status_code == 200


class TestTelemetry:
    async def test_latest_before_any_frame(self, client: AsyncClient) -> None:
        """프레임을 한 번도 못 받았어도 상태를 지어내지 않는다."""
        body = await _register(client)

        response = await client.get(
            f"/devices/{body['deviceId']}/telemetry/latest",
            headers=_auth(body["deviceToken"]),
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["state"] == "WARMUP"
        assert payload["module"]["lastSeen"] is None

    async def test_latest_returns_camel_case_contract(
        self, client: AsyncClient, session: Session, now: datetime
    ) -> None:
        body = await _register(client)
        device_id = _device_row_id(session, body["deviceId"])
        SqlAlchemyReadingRepository(session).add_if_absent(
            Reading(
                device_id=device_id,
                seq=7,
                measured_at=now,
                received_at=now,
                frame_version=1,
                state=AlertState.WATCH,
                latched=False,
                channels=(ChannelReading(channel=GasChannel.VOC, deviation=3.1, slope=2.4),),
                signature=SignatureFlags(rise=True, hold=False, no_recover=True, hold_s=18),
                temp_c=24.5,
                humidity_pct=41.0,
                batt_mv=3960,
                lat=37.5573,
                lon=127.0329,
                rssi=-74,
            )
        )
        session.commit()

        payload = (
            await client.get(
                f"/devices/{body['deviceId']}/telemetry/latest",
                headers=_auth(body["deviceToken"]),
            )
        ).json()

        assert payload["state"] == "WATCH"
        assert payload["gas"] == {"devZ": 3.1, "slope": 2.4}
        assert payload["signature"]["noRecover"] is True
        assert payload["signature"]["holdS"] == 18
        assert payload["location"] == {"lat": 37.5573, "lon": 127.0329}
        assert payload["module"]["battMv"] == 3960
        assert payload["module"]["rssi"] == -74

    async def test_raw_sensor_fields_are_absent(
        self, client: AsyncClient, session: Session, now: datetime
    ) -> None:
        """raw는 서버가 채울 수 없다 (정합화 B2). 0으로 채워 내보내지 않는다."""
        body = await _register(client)
        device_id = _device_row_id(session, body["deviceId"])
        SqlAlchemyReadingRepository(session).add_if_absent(
            Reading(
                device_id=device_id,
                seq=1,
                measured_at=now,
                received_at=now,
                frame_version=1,
                state=AlertState.NORMAL,
            )
        )
        session.commit()

        payload = (
            await client.get(
                f"/devices/{body['deviceId']}/telemetry/latest",
                headers=_auth(body["deviceToken"]),
            )
        ).json()

        assert "sraw" not in payload["gas"]
        assert "mv" not in payload["h2"]

    async def test_history_aggregates_by_hour(self, client: AsyncClient, session: Session) -> None:
        body = await _register(client)
        device_id = _device_row_id(session, body["deviceId"])
        readings = SqlAlchemyReadingRepository(session)
        base = datetime(2026, 8, 8, 14, 0, tzinfo=UTC)
        for index, state in enumerate([AlertState.NORMAL, AlertState.WATCH]):
            readings.add_if_absent(
                Reading(
                    device_id=device_id,
                    seq=index,
                    measured_at=base + timedelta(minutes=5 * index),
                    received_at=base,
                    frame_version=1,
                    state=state,
                    channels=(
                        ChannelReading(channel=GasChannel.VOC, deviation=float(index), slope=None),
                    ),
                )
            )
        session.commit()

        payload = (
            await client.get(
                f"/devices/{body['deviceId']}/telemetry/history",
                headers=_auth(body["deviceToken"]),
                params={"date": "2026-08-08"},
            )
        ).json()

        assert len(payload["samples"]) == 1
        sample = payload["samples"][0]
        assert sample["hour"] == "14:00"
        # 한 시간 안 최악값을 쓴다 — 평균 내면 경보가 묻힌다
        assert sample["state"] == "WATCH"
        assert sample["gas"]["devZ"] == pytest.approx(0.5)


class TestAlarmRelease:
    async def test_release_without_active_alarm_is_forbidden(self, client: AsyncClient) -> None:
        body = await _register(client)

        response = await client.post(
            f"/devices/{body['deviceId']}/alarm/release",
            headers=_auth(body["deviceToken"]),
            json={},
        )

        assert response.status_code == 403
        assert response.json()["error"] == "not_allowed"

    async def test_release_acknowledges_active_alarm(
        self, client: AsyncClient, session: Session, now: datetime
    ) -> None:
        body = await _register(client)
        device_id = _device_row_id(session, body["deviceId"])
        alerts = SqlAlchemyAlertRepository(session)
        alerts.add(
            Alert(
                device_id=device_id,
                from_state=AlertState.WATCH,
                to_state=AlertState.ALARM,
                occurred_at=now,
                detected_at=now,
            )
        )
        session.commit()

        response = await client.post(
            f"/devices/{body['deviceId']}/alarm/release",
            headers=_auth(body["deviceToken"]),
            json={"note": "현장 확인 완료"},
        )

        assert response.status_code == 200
        assert response.json() == {"released": True}
        assert alerts.list_active() == []

    async def test_release_is_recorded_as_event(
        self, client: AsyncClient, session: Session, now: datetime
    ) -> None:
        body = await _register(client)
        device_id = _device_row_id(session, body["deviceId"])
        SqlAlchemyAlertRepository(session).add(
            Alert(
                device_id=device_id,
                from_state=AlertState.NORMAL,
                to_state=AlertState.ALARM,
                occurred_at=now,
                detected_at=now,
            )
        )
        session.commit()

        await client.post(
            f"/devices/{body['deviceId']}/alarm/release",
            headers=_auth(body["deviceToken"]),
            json={},
        )
        session.rollback()  # 읽기 트랜잭션 스냅샷을 끊어야 새 커밋이 보인다

        # 서버는 SystemClock으로 기록한다 — fixture 시각 기준 창을 쓰면 어긋난다.
        events = SqlAlchemyEventRepository(session).list_since(
            device_id, since=datetime(2020, 1, 1, tzinfo=UTC), limit=10
        )
        assert [e.kind for e in events] == [EventKind.ACTION]
        assert "경보 해제" in events[0].description


class TestEventList:
    async def test_events_since(self, client: AsyncClient, session: Session, now: datetime) -> None:
        body = await _register(client)
        device_id = _device_row_id(session, body["deviceId"])
        SqlAlchemyEventRepository(session).add(
            Event(
                device_id=device_id,
                kind=EventKind.SUPPRESSED,
                occurred_at=now,
                description="습도 급변으로 가스 채널 승격 보류 (오경보 아님)",
            )
        )
        session.commit()

        payload = (
            await client.get(
                f"/devices/{body['deviceId']}/events",
                headers=_auth(body["deviceToken"]),
                params={"since": (now - timedelta(hours=1)).isoformat()},
            )
        ).json()

        assert len(payload["items"]) == 1
        assert payload["items"][0]["kind"] == "suppressed"
        assert payload["items"][0]["id"].startswith("evt_")


class TestFleetComparison:
    async def test_fleet_size_counts_registered_devices(self, client: AsyncClient) -> None:
        body = await _register(client)
        await _register(client, "11:22:33:44:55:66")

        payload = (
            await client.get(
                f"/devices/{body['deviceId']}/fleet-comparison",
                headers=_auth(body["deviceToken"]),
            )
        ).json()

        assert payload["fleetSize"] == 2
        assert payload["myLevel"] == "NORMAL"


def _device_row_id(session: Session, public_id: str) -> int:
    from app.infrastructure.db.repositories import SqlAlchemyDeviceRepository

    device = SqlAlchemyDeviceRepository(session).get_by_public_id(public_id)
    assert device is not None
    return device.id or 0
