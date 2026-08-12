"""Expo 발송 어댑터 단위 테스트.

Expo 응답 해석이 틀리면 죽은 토큰을 계속 재시도하거나(실패율 누적) 살아 있는
토큰을 비활성화한다(알람 미수신). fake sender로는 이 판정을 검증할 수 없다.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import httpx
import pytest

from app.infrastructure.push.expo import ExpoPushSender
from tests.builders import a_device, an_alert

_NOW = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)


def _sender(handler: Any) -> ExpoPushSender:
    return ExpoPushSender(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def _responds(payload: dict[str, Any], status_code: int = 200) -> Any:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload)

    return handler


async def _send(handler: Any) -> Any:
    sender = _sender(handler)
    return await sender.send(
        token="ExponentPushToken[x]", alert=an_alert(_NOW, key=1), device=a_device()
    )


class TestTicketInterpretation:
    async def test_ok_ticket_is_delivered(self) -> None:
        result = await _send(_responds({"data": {"status": "ok", "id": "abc"}}))

        assert result.delivered is True
        assert result.permanent_failure is False

    async def test_ok_ticket_in_list_form_is_delivered(self) -> None:
        """Expo는 단건도 배열로 돌려줄 수 있다."""
        result = await _send(_responds({"data": [{"status": "ok", "id": "abc"}]}))

        assert result.delivered is True

    async def test_dead_token_is_permanent(self) -> None:
        result = await _send(
            _responds(
                {
                    "data": {
                        "status": "error",
                        "message": "not a registered push token",
                        "details": {"error": "DeviceNotRegistered"},
                    }
                }
            )
        )

        assert result.delivered is False
        assert result.error_code == "DeviceNotRegistered"
        assert result.permanent_failure is True

    async def test_rate_limit_is_retryable(self) -> None:
        result = await _send(
            _responds({"data": {"status": "error", "details": {"error": "MessageRateExceeded"}}})
        )

        assert result.delivered is False
        assert result.permanent_failure is False

    async def test_error_without_details_falls_back_to_message(self) -> None:
        result = await _send(_responds({"data": {"status": "error", "message": "boom"}}))

        assert result.error_code == "boom"
        assert result.permanent_failure is False

    async def test_empty_body_is_not_treated_as_success(self) -> None:
        result = await _send(_responds({}))

        assert result.delivered is False
        assert result.error_code == "unknown"


class TestTransportFailure:
    async def test_server_error_is_retryable(self) -> None:
        result = await _send(_responds({"errors": []}, status_code=502))

        assert result.delivered is False
        assert result.permanent_failure is False

    async def test_network_error_is_retryable(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("no route", request=request)

        result = await _send(handler)

        assert result.delivered is False
        assert result.error_code == "ConnectError"
        assert result.permanent_failure is False


class TestRequestShape:
    async def test_sends_high_priority_message_to_the_token(self) -> None:
        seen: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(200, json={"data": {"status": "ok"}})

        await _send(handler)

        assert len(seen) == 1
        body = seen[0].read().decode()
        assert "ExponentPushToken[x]" in body
        assert '"priority": "high"' in body or '"priority":"high"' in body

    async def test_data_addresses_the_device_by_mac(self) -> None:
        """앱은 MAC으로 기기 화면을 연다. public_id는 v1에서 경로가 아니다."""
        seen: list[dict[str, Any]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(json.loads(request.read()))
            return httpx.Response(200, json={"data": {"status": "ok"}})

        device = a_device()
        await _sender(handler).send(
            token="ExponentPushToken[x]", alert=an_alert(_NOW, key=1), device=device
        )

        assert seen[0]["data"] == {
            "deviceMac": device.mac,
            "status": "ALARM",
            "alertId": "1",
        }


class TestInjectedClientOwnership:
    async def test_injected_client_is_not_closed(self) -> None:
        """호출자가 준 client를 어댑터가 닫으면 다음 발송이 죽는다."""
        client = httpx.AsyncClient(
            transport=httpx.MockTransport(lambda _r: httpx.Response(200, json={"data": {}}))
        )
        sender = ExpoPushSender(client=client)

        await sender.send(token="t", alert=an_alert(_NOW, key=1), device=a_device())

        assert client.is_closed is False
        await client.aclose()


@pytest.fixture(autouse=True)
def _no_real_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """MockTransport를 안 거치는 경로가 생기면 실제 요청 대신 여기서 터진다."""
    monkeypatch.setattr(
        httpx.AsyncHTTPTransport,
        "handle_async_request",
        lambda *_args, **_kwargs: pytest.fail("실제 네트워크 요청이 나갔다"),
    )
