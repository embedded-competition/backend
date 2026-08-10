from __future__ import annotations

import logging
from typing import Any

import httpx

from app.domain.alerting import Alert
from app.domain.device import Device
from app.domain.ports.push_sender import PushResult
from app.infrastructure.push import messages

logger = logging.getLogger(__name__)

_ENDPOINT = "https://exp.host/--/api/v2/push/send"
_PERMANENT_ERRORS = frozenset({"DeviceNotRegistered", "InvalidCredentials"})


class ExpoPushSender:
    def __init__(self, *, timeout_s: float = 10.0, client: httpx.AsyncClient | None = None) -> None:
        self._timeout_s = timeout_s
        self._client = client
        self._owns_client = client is None

    async def send(self, *, token: str, alert: Alert, device: Device) -> PushResult:
        message = messages.build(alert, device)
        payload = {
            "to": token,
            "title": message.title,
            "body": message.body,
            "data": message.data,
            "priority": "high",
        }
        client = self._client or httpx.AsyncClient(timeout=self._timeout_s)
        try:
            response = await client.post(_ENDPOINT, json=payload)
            response.raise_for_status()
            return _interpret(response.json())
        except httpx.HTTPError as exc:
            logger.warning("expo push failed", extra={"error": type(exc).__name__})
            return PushResult(delivered=False, error_code=type(exc).__name__)
        finally:
            if self._owns_client:
                await client.aclose()


def _interpret(body: dict[str, Any]) -> PushResult:
    ticket = body.get("data") or {}
    if isinstance(ticket, list):
        ticket = ticket[0] if ticket else {}
    if ticket.get("status") == "ok":
        return PushResult(delivered=True)
    error_code = (ticket.get("details") or {}).get("error") or ticket.get("message")
    return PushResult(
        delivered=False,
        error_code=str(error_code) if error_code else "unknown",
        permanent_failure=error_code in _PERMANENT_ERRORS,
    )


class LoggingPushSender:
    async def send(self, *, token: str, alert: Alert, device: Device) -> PushResult:
        message = messages.build(alert, device)
        logger.info(
            "push (logging only)",
            extra={
                "token": _mask(token),
                "device": device.public_id,
                "state": alert.to_state.value,
                "title": message.title,
            },
        )
        return PushResult(delivered=True)


_MASKABLE_LENGTH = 20


def _mask(token: str) -> str:
    return f"{token[:12]}…{token[-4:]}" if len(token) > _MASKABLE_LENGTH else "…"
