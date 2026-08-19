from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict, dataclass

from app.domain.alerting import Alert
from app.domain.device import Device
from app.domain.ports.clock import Clock
from app.domain.ports.push_sender import PushResult, PushSender
from app.domain.push import PushDelivery
from app.infrastructure.db.repositories.push_deliveries import SqlAlchemyPushDeliveryRepository
from app.infrastructure.db.repositories.push_tokens import SqlAlchemyPushTokenRepository

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DispatchReport:
    attempted: int
    delivered: int
    deactivated: int

    def as_dict(self) -> dict[str, int]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class NotificationService:
    push_tokens: SqlAlchemyPushTokenRepository
    deliveries: SqlAlchemyPushDeliveryRepository
    sender: PushSender
    clock: Clock
    max_attempts: int = 3
    backoff_base_s: float = 1.0

    async def dispatch(self, alert: Alert, device: Device) -> DispatchReport:
        tokens = self.push_tokens.list_active(device.key)
        if not tokens:
            logger.info("no active push token", extra={"device": device.public_id})
            return DispatchReport(attempted=0, delivered=0, deactivated=0)

        delivered = deactivated = 0
        for token in tokens:
            outcome = await self._send_with_retry(alert, device, token.token)
            if outcome.delivered:
                delivered += 1
            elif outcome.permanent_failure:
                token.deactivate(outcome.error_code or "permanent_failure")
                self.push_tokens.save(token)
                deactivated += 1
        return DispatchReport(attempted=len(tokens), delivered=delivered, deactivated=deactivated)

    async def _send_with_retry(self, alert: Alert, device: Device, token: str) -> _Outcome:
        last = _Outcome(delivered=False, error_code=None, permanent_failure=False)
        for attempt in range(1, self.max_attempts + 1):
            result = await self.sender.send(token=token, alert=alert, device=device)
            self.deliveries.add(
                PushDelivery(
                    alert_id=alert.key,
                    token=token,
                    attempt=attempt,
                    status="sent" if result.delivered else _failure_status(result),
                    error_code=result.error_code,
                    sent_at=self.clock.now(),
                )
            )
            last = _Outcome(
                delivered=result.delivered,
                error_code=result.error_code,
                permanent_failure=result.permanent_failure,
            )
            if result.delivered or result.permanent_failure:
                return last
            if attempt < self.max_attempts:
                await asyncio.sleep(self.backoff_base_s * (2 ** (attempt - 1)))
        return last


@dataclass(frozen=True, slots=True)
class _Outcome:
    delivered: bool
    error_code: str | None
    permanent_failure: bool


def _failure_status(result: PushResult) -> str:
    return "failed_permanent" if result.permanent_failure else "failed_retryable"
