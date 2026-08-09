"""요청 밖(백그라운드 task) 조립. 요청 스코프 조립은 providers.py."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.ingest_service import IngestService
from app.core.notification_service import NotificationService
from app.domain.ports.push_sender import PushSender
from app.infrastructure.clock import SystemClock
from app.infrastructure.db.repositories.alerts import SqlAlchemyAlertRepository
from app.infrastructure.db.repositories.devices import SqlAlchemyDeviceRepository
from app.infrastructure.db.repositories.events import SqlAlchemyEventRepository
from app.infrastructure.db.repositories.push_deliveries import SqlAlchemyPushDeliveryRepository
from app.infrastructure.db.repositories.push_tokens import SqlAlchemyPushTokenRepository
from app.infrastructure.db.repositories.readings import SqlAlchemyReadingRepository
from app.infrastructure.push.expo import ExpoPushSender, LoggingPushSender


def session_scope_factory(
    factory: sessionmaker[Session],
) -> Callable[[], AbstractContextManager[Session]]:
    @contextmanager
    def scope() -> Iterator[Session]:
        """트랜잭션 경계 1개. 수신 task가 프레임 단위로 연다."""
        session = factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return scope


def build_ingest_service(session: Session) -> IngestService:
    return IngestService(
        devices=SqlAlchemyDeviceRepository(session),
        readings=SqlAlchemyReadingRepository(session),
        alerts=SqlAlchemyAlertRepository(session),
        events=SqlAlchemyEventRepository(session),
        clock=SystemClock(),
    )


def create_push_sender(settings: Settings) -> PushSender:
    """자격증명이 없으면 로그만 남기는 구현 — 알람 흐름은 그대로 검증된다."""
    if settings.fcm_credentials_path is None:
        return LoggingPushSender()
    return ExpoPushSender(timeout_s=settings.push_timeout_s)


def notifier_factory(
    settings: Settings, sender: PushSender
) -> Callable[[Session], NotificationService]:
    def build(session: Session) -> NotificationService:
        return NotificationService(
            push_tokens=SqlAlchemyPushTokenRepository(session),
            deliveries=SqlAlchemyPushDeliveryRepository(session),
            sender=sender,
            clock=SystemClock(),
            max_attempts=settings.push_max_attempts,
        )

    return build
