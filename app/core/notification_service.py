"""알람 푸시 디스패치 유스케이스.

**커밋 이후에 호출한다** — 커밋 전 발송은 롤백 시 유령 알림을 만든다.
발송 실패가 측정값 저장을 되돌리지 않는다.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from app.domain.models import Alert, Device, PushDelivery
from app.domain.ports import Clock, PushSender
from app.infrastructure.db.repositories import (
    SqlAlchemyPushDeliveryRepository,
    SqlAlchemyPushTokenRepository,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DispatchReport:
    attempted: int
    delivered: int
    deactivated: int

    @property
    def failed(self) -> int:
        return self.attempted - self.delivered


@dataclass(frozen=True, slots=True)
class NotificationService:
    push_tokens: SqlAlchemyPushTokenRepository
    deliveries: SqlAlchemyPushDeliveryRepository
    sender: PushSender
    clock: Clock
    max_attempts: int = 3
    backoff_base_s: float = 1.0

    async def dispatch(self, alert: Alert, device: Device) -> DispatchReport:
        tokens = self.push_tokens.list_active(device.id or 0)
        if not tokens:
            logger.info("no active push token", extra={"device": device.public_id})
            return DispatchReport(attempted=0, delivered=0, deactivated=0)

        delivered = deactivated = 0
        for token in tokens:
            outcome = await self._send_with_retry(alert, device, token.token)
            if outcome.delivered:
                delivered += 1
            elif outcome.permanent_failure:
                # 무효 토큰을 방치하면 실패율이 계속 쌓인다.
                token.deactivate(outcome.error_code or "permanent_failure")
                self.push_tokens.save(token)
                deactivated += 1
        return DispatchReport(attempted=len(tokens), delivered=delivered, deactivated=deactivated)

    async def _send_with_retry(self, alert: Alert, device: Device, token: str) -> _Outcome:
        """지수 백오프 + 상한. 영구 실패는 즉시 중단한다."""
        last = _Outcome(delivered=False, error_code=None, permanent_failure=False)
        for attempt in range(1, self.max_attempts + 1):
            result = await self.sender.send(token=token, alert=alert, device=device)
            self.deliveries.add(
                PushDelivery(
                    alert_id=alert.id or 0,
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


def _failure_status(result: object) -> str:
    permanent = getattr(result, "permanent_failure", False)
    return "failed_permanent" if permanent else "failed_retryable"
