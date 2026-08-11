"""수신 루프 통합 테스트 — fake source로 하드웨어 없이 전 경로를 태운다."""

from __future__ import annotations

import logging
from datetime import datetime

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.notification_service import NotificationService
from app.domain.device import Device
from app.domain.ports.frame_source import RawFrame
from app.domain.ports.push_sender import PushResult
from app.domain.push import PushToken
from app.domain.value_objects import AlertState
from app.infrastructure.clock import SystemClock
from app.infrastructure.db.repositories.alerts import SqlAlchemyAlertRepository
from app.infrastructure.db.repositories.devices import SqlAlchemyDeviceRepository
from app.infrastructure.db.repositories.push_deliveries import SqlAlchemyPushDeliveryRepository
from app.infrastructure.db.repositories.push_tokens import SqlAlchemyPushTokenRepository
from app.infrastructure.db.repositories.readings import SqlAlchemyReadingRepository
from app.infrastructure.lora.frame import build_frame
from app.infrastructure.lora.scenario import DEFAULT_SCENARIO, ScenarioFrameFactory
from app.runtime import wiring
from app.runtime.receiver import FrameReceiver
from tests.fakes.lora import ReplayFrameSource
from tests.fakes.push import RecordingPushSender

HW_ID = "aabbccddeeff"
MAC = "AA:BB:CC:DD:EE:FF"


def _settings() -> Settings:
    return Settings(environment="local", management_phone="01029015899")


@pytest.fixture
def registered(session: Session, now: datetime) -> Device:
    device = SqlAlchemyDeviceRepository(session).save(
        Device(public_id="dev_test01", mac=MAC, label="1호차", registered_at=now)
    )
    SqlAlchemyPushTokenRepository(session).upsert(
        PushToken(
            device_id=device.key,
            token="ExponentPushToken[demo]",
            registered_at=now,
        )
    )
    session.commit()
    return device


@pytest.fixture
def sender() -> RecordingPushSender:
    return RecordingPushSender()


def _receiver(
    factory: sessionmaker[Session], sender: RecordingPushSender, frames: list[RawFrame]
) -> FrameReceiver:
    def notifier(session: Session) -> NotificationService:
        return NotificationService(
            push_tokens=SqlAlchemyPushTokenRepository(session),
            deliveries=SqlAlchemyPushDeliveryRepository(session),
            sender=sender,
            clock=SystemClock(),
            max_attempts=2,
            backoff_base_s=0.0,  # 테스트가 백오프를 기다리지 않게
        )

    return FrameReceiver(
        source=ReplayFrameSource(frames),
        session_scope=wiring.session_scope_factory(factory),
        ingest_factory=wiring.ingest_factory(_settings()),
        notifier_factory=notifier,
    )


def _scenario_frames(count: int, now: datetime) -> list[RawFrame]:
    factory = ScenarioFrameFactory(HW_ID, with_gps=False)
    return [
        RawFrame(
            payload=build_frame(factory.build(seq, at=now)),
            received_at=now,
            rssi=-74,
            snr=7.0,
        )
        for seq in range(count)
    ]


class TestReceiveLoop:
    async def test_scenario_is_stored(
        self,
        session_factory: sessionmaker[Session],
        session: Session,
        sender: RecordingPushSender,
        registered: Device,
        now: datetime,
    ) -> None:
        receiver = _receiver(session_factory, sender, _scenario_frames(len(DEFAULT_SCENARIO), now))

        await receiver.run()

        assert receiver.stats.received == len(DEFAULT_SCENARIO)
        # 같은 measured_at + 다른 seq라 전부 저장된다
        assert receiver.stats.stored == len(DEFAULT_SCENARIO)
        assert receiver.stats.parse_error == 0

    async def test_transitions_trigger_push(
        self,
        session_factory: sessionmaker[Session],
        sender: RecordingPushSender,
        registered: Device,
        now: datetime,
    ) -> None:
        receiver = _receiver(session_factory, sender, _scenario_frames(len(DEFAULT_SCENARIO), now))

        await receiver.run()

        # NORMAL→WATCH, WATCH→ALARM 두 번만 발송된다 (같은 상태 유지엔 안 보냄)
        states = [state for _, state in sender.sent]
        assert states == [AlertState.WATCH.value, AlertState.ALARM.value]

    async def test_corrupted_frame_does_not_stop_loop(
        self,
        session_factory: sessionmaker[Session],
        sender: RecordingPushSender,
        registered: Device,
        now: datetime,
    ) -> None:
        frames = _scenario_frames(3, now)
        broken = bytearray(frames[1].payload)
        broken[10] ^= 0xFF
        frames[1] = RawFrame(payload=bytes(broken), received_at=now)

        receiver = _receiver(session_factory, sender, frames)
        await receiver.run()

        assert receiver.stats.crc_error == 1
        assert receiver.stats.stored == 2  # 나머지는 정상 처리

    async def test_unknown_node_is_adopted_not_dropped(
        self,
        session_factory: sessionmaker[Session],
        session: Session,
        sender: RecordingPushSender,
        now: datetime,
    ) -> None:
        """등록 경로가 없으므로 처음 보는 노드의 프레임도 버리지 않는다."""
        receiver = _receiver(session_factory, sender, _scenario_frames(2, now))

        await receiver.run()

        assert receiver.stats.stored == 2
        assert receiver.stats.unknown_device == 0
        assert SqlAlchemyDeviceRepository(session).get_by_mac(MAC) is not None


class TestDispatchLogging:
    async def test_successful_dispatch_is_not_logged_as_failure(
        self,
        session_factory: sessionmaker[Session],
        sender: RecordingPushSender,
        registered: Device,
        now: datetime,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """발송은 성공했는데 로그만 실패로 남으면 운영자는 푸시가 죽은 줄로 읽는다.

        blanket except가 삼키므로 DB 단정만으로는 드러나지 않는다.
        """
        receiver = _receiver(session_factory, sender, _scenario_frames(len(DEFAULT_SCENARIO), now))

        with caplog.at_level(logging.INFO, logger="app.runtime.receiver"):
            await receiver.run()

        assert sender.sent, "이 시나리오는 발송이 일어나야 한다"
        assert "alert dispatch failed" not in caplog.text
        dispatched = [r for r in caplog.records if r.getMessage() == "alert dispatched"]
        assert dispatched
        assert dispatched[0].attempted >= 1  # type: ignore[attr-defined]


class TestPushRetry:
    async def test_permanent_failure_deactivates_token(
        self,
        session_factory: sessionmaker[Session],
        session: Session,
        registered: Device,
        now: datetime,
    ) -> None:
        sender = RecordingPushSender(
            results=[
                PushResult(
                    delivered=False,
                    error_code="DeviceNotRegistered",
                    permanent_failure=True,
                )
            ]
        )
        receiver = _receiver(session_factory, sender, _scenario_frames(len(DEFAULT_SCENARIO), now))

        await receiver.run()
        session.rollback()

        tokens = SqlAlchemyPushTokenRepository(session).list_active(registered.key)
        assert tokens == []  # 무효 토큰을 방치하면 실패율이 계속 쌓인다

    async def test_alerts_are_recorded(
        self,
        session_factory: sessionmaker[Session],
        session: Session,
        sender: RecordingPushSender,
        registered: Device,
        now: datetime,
    ) -> None:
        receiver = _receiver(session_factory, sender, _scenario_frames(len(DEFAULT_SCENARIO), now))

        await receiver.run()
        session.rollback()

        alerts = SqlAlchemyAlertRepository(session).list_active_for(registered.key)
        assert len(alerts) == 2
        assert SqlAlchemyReadingRepository(session).latest(registered.key)
