"""수신 루프 통합 테스트 — fake source로 하드웨어 없이 전 경로를 태운다."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace
from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.notification_service import NotificationService
from app.domain.device import Device
from app.domain.frames import TelemetryFrame
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
from app.runtime import wiring
from app.runtime.receiver import FrameParser, FrameReceiver, parse_wire_frame
from tests.fakes.lora import ReplayFrameSource, SilentFrameSource
from tests.fakes.push import RecordingPushSender
from tests.fakes.scenario import DEFAULT_SCENARIO, ScenarioFrameFactory

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


def _with_states(*states: AlertState) -> FrameParser:
    """프레임에는 판정이 없다 — 알림 경로를 태우려면 상태를 테스트가 만든다.

    노드가 상태를 보내지 않으므로 수신 경로만으로는 전이가 생기지 않는다. 알림·재시도는
    프레임 포맷과 무관한 관심사라 여기서 분리한다.
    """
    remaining = iter(states)

    def parse(raw: RawFrame) -> TelemetryFrame:
        return replace(parse_wire_frame(raw), state=next(remaining))

    return parse


_RISING = (
    AlertState.NORMAL,
    AlertState.NORMAL,
    AlertState.WATCH,
    AlertState.WATCH,
    AlertState.ALARM,
    AlertState.ALARM,
)


def _receiver(
    factory: sessionmaker[Session],
    sender: RecordingPushSender,
    frames: list[RawFrame],
    *,
    parse: FrameParser = parse_wire_frame,
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
        parse=parse,
    )


def _scenario_frames(
    count: int, now: datetime, *, apart: timedelta = timedelta(seconds=1)
) -> list[RawFrame]:
    """수신 시각이 판독을 가르는 유일한 축이다 — 노드가 seq를 보내지 않는다."""
    factory = ScenarioFrameFactory(HW_ID)
    return [
        RawFrame(
            payload=build_frame(factory.build(step)),
            received_at=now + apart * step,
            rssi=-74,
            snr=7.0,
        )
        for step in range(count)
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
        # seq가 없으므로 수신 시각이 판독을 가른다
        assert receiver.stats.stored == len(DEFAULT_SCENARIO)
        assert receiver.stats.parse_error == 0

    async def test_transitions_trigger_push(
        self,
        session_factory: sessionmaker[Session],
        sender: RecordingPushSender,
        registered: Device,
        now: datetime,
    ) -> None:
        receiver = _receiver(
            session_factory,
            sender,
            _scenario_frames(len(DEFAULT_SCENARIO), now),
            parse=_with_states(*_RISING),
        )

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
        receiver = _receiver(
            session_factory,
            sender,
            _scenario_frames(len(DEFAULT_SCENARIO), now),
            parse=_with_states(*_RISING),
        )

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
        receiver = _receiver(
            session_factory,
            sender,
            _scenario_frames(len(DEFAULT_SCENARIO), now),
            parse=_with_states(*_RISING),
        )

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
        receiver = _receiver(
            session_factory,
            sender,
            _scenario_frames(len(DEFAULT_SCENARIO), now),
            parse=_with_states(*_RISING),
        )

        await receiver.run()
        session.rollback()

        alerts = SqlAlchemyAlertRepository(session).list_active_for(registered.key)
        assert len(alerts) == 2
        assert SqlAlchemyReadingRepository(session).latest(registered.key)


class TestObservability:
    async def test_silence_is_reported(
        self,
        session_factory: sessionmaker[Session],
        sender: RecordingPushSender,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """수신이 0이면 로그도 0이라 죽은 것과 구별되지 않는다. 침묵을 말하게 한다."""
        receiver = _receiver(session_factory, sender, [])
        receiver.source = SilentFrameSource()
        receiver.silence_report_s = 0.01

        with caplog.at_level(logging.WARNING, logger="app.runtime.receiver"):
            await _run_until_logged(receiver, "receiver silent")

        silent = [r for r in caplog.records if r.getMessage() == "receiver silent"]
        assert silent[0].silent_s >= 0  # type: ignore[attr-defined]
        assert silent[0].received == 0  # type: ignore[attr-defined]

    async def test_each_frame_is_traceable_at_debug(
        self,
        session_factory: sessionmaker[Session],
        sender: RecordingPushSender,
        registered: Device,
        now: datetime,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """요약만 있으면 개별 프레임을 되짚을 수 없다 — 링크 품질도 거기 있다."""
        receiver = _receiver(session_factory, sender, _scenario_frames(1, now))

        with caplog.at_level(logging.DEBUG, logger="app.runtime.receiver"):
            await receiver.run()

        received = [r for r in caplog.records if r.getMessage() == "frame received"]
        assert len(received) == 1
        assert received[0].hw_id == HW_ID  # type: ignore[attr-defined]
        assert received[0].rssi == -74  # type: ignore[attr-defined]

    async def test_stats_are_reported_once_the_interval_passes(
        self,
        session_factory: sessionmaker[Session],
        sender: RecordingPushSender,
        registered: Device,
        now: datetime,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        frames = _scenario_frames(25, now, apart=timedelta(minutes=1))
        receiver = _receiver(session_factory, sender, frames)

        with caplog.at_level(logging.INFO, logger="app.runtime.receiver"):
            await receiver.run()

        reports = [r for r in caplog.records if r.getMessage() == "receive stats"]
        assert receiver.report_every == timedelta(minutes=10)
        assert len(reports) == 2

    async def test_a_fast_source_does_not_flood_the_log(
        self,
        session_factory: sessionmaker[Session],
        sender: RecordingPushSender,
        registered: Device,
        now: datetime,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """개수로 끊으면 초당 여러 장을 내는 소스가 로그를 덮는다.

        시뮬레이터가 그렇다. 요약 한 줄이 몇 초마다 나오면 정작 읽어야 하는
        무선 침묵 경고가 그 사이에 파묻힌다.
        """
        frames = _scenario_frames(200, now, apart=timedelta(milliseconds=600))
        receiver = _receiver(session_factory, sender, frames)

        with caplog.at_level(logging.INFO, logger="app.runtime.receiver"):
            await receiver.run()

        assert not [r for r in caplog.records if r.getMessage() == "receive stats"]


class _WakeOnMessage(logging.Handler):
    """찾는 로그가 나온 순간을 event로 알린다 — 폴링하면 느리거나 불안정하다."""

    def __init__(self, message: str, seen: asyncio.Event) -> None:
        super().__init__()
        self._message = message
        self._seen = seen

    def emit(self, record: logging.LogRecord) -> None:
        if record.getMessage() == self._message:
            self._seen.set()


async def _run_until_logged(receiver: FrameReceiver, message: str) -> None:
    """무선은 스스로 끝나지 않는다. 원하는 로그가 나오면 실제 종료 경로로 세운다."""
    seen = asyncio.Event()
    handler = _WakeOnMessage(message, seen)
    logger = logging.getLogger("app.runtime.receiver")
    logger.addHandler(handler)

    task = asyncio.create_task(receiver.run())
    try:
        async with asyncio.timeout(5):
            await seen.wait()
    finally:
        logger.removeHandler(handler)
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
