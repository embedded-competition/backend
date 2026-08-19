from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from datetime import timedelta

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


def ingest_factory(settings: Settings) -> Callable[[Session], IngestService]:
    def build(session: Session) -> IngestService:
        return IngestService(
            devices=SqlAlchemyDeviceRepository(session),
            readings=SqlAlchemyReadingRepository(session),
            alerts=SqlAlchemyAlertRepository(session),
            events=SqlAlchemyEventRepository(session),
            clock=SystemClock(),
            default_management_phone=settings.management_phone,
            slope_window=timedelta(seconds=settings.offline_threshold_s),
        )

    return build


def create_push_sender(settings: Settings) -> PushSender:
    if settings.push_delivery == "log":
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
