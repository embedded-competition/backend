"""수신 파이프라인 통합 테스트 — 프레임 → 저장 → 전이 → 알람."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from app.core.ingest_service import IngestService
from app.domain.device import Device
from app.domain.frames import TelemetryFrame
from app.domain.measurements import Measure
from app.domain.ports.frame_source import RawFrame
from app.domain.value_objects import AlertState, DeviceId, GasChannel, Period
from app.infrastructure.clock import SystemClock
from app.infrastructure.db.repositories.alerts import SqlAlchemyAlertRepository
from app.infrastructure.db.repositories.devices import SqlAlchemyDeviceRepository
from app.infrastructure.db.repositories.events import SqlAlchemyEventRepository
from app.infrastructure.db.repositories.readings import SqlAlchemyReadingRepository
from app.infrastructure.lora.frame import WIRE_FORMAT_ID

HW_ID = "aabbccddeeff"
MAC = "AA:BB:CC:DD:EE:FF"
MANAGEMENT_PHONE = "01029015899"


@pytest.fixture
def ingest(session: Session) -> IngestService:
    return IngestService(
        devices=SqlAlchemyDeviceRepository(session),
        readings=SqlAlchemyReadingRepository(session),
        alerts=SqlAlchemyAlertRepository(session),
        events=SqlAlchemyEventRepository(session),
        clock=SystemClock(),
        default_management_phone=MANAGEMENT_PHONE,
    )


@pytest.fixture
def registered(session: Session, now: datetime) -> Device:
    """앱이 MAC으로 먼저 등록한 상태 — 노드는 아직 프레임을 안 보냈다."""
    return SqlAlchemyDeviceRepository(session).save(
        Device(public_id="dev_test01", mac=MAC, label="1호차", registered_at=now)
    )


def _frame(seq: int, state: AlertState, at: datetime) -> TelemetryFrame:
    return TelemetryFrame(
        version=WIRE_FORMAT_ID,
        hw_id=DeviceId(HW_ID),
        seq=seq,
        measured_at=at,
        state=state,
        latched=state is AlertState.ALARM,
        values={Measure.VOC_DEV: 3.1, Measure.VOC_SLOPE: 2.4},
        batt_mv=3960,
    )


def _raw(at: datetime) -> RawFrame:
    return RawFrame(payload=b"", received_at=at, rssi=-74, snr=7.5)


class TestDeviceResolution:
    def test_first_frame_links_hw_id_to_registered_mac(
        self, ingest: IngestService, registered: Device, now: datetime
    ) -> None:
        outcome = ingest.ingest(_frame(1, AlertState.NORMAL, now), _raw(now))

        assert outcome.device.id == registered.id
        assert outcome.device.hw_id == DeviceId(HW_ID)

    def test_unknown_node_is_adopted(self, ingest: IngestService, now: datetime) -> None:
        """등록 경로가 없으므로 첫 프레임이 기기를 만든다.

        MAC은 hw_id에서 유도하고, 관리실 번호는 설정 기본값을 물려받는다 — 앱이
        경보 화면에서 걸 번호를 받을 다른 통로가 없다.
        """
        unknown = replace(_frame(1, AlertState.NORMAL, now), hw_id=DeviceId("112233445566"))

        outcome = ingest.ingest(unknown, _raw(now))

        assert outcome.device.mac == "11:22:33:44:55:66"
        assert outcome.device.hw_id == DeviceId("112233445566")
        assert outcome.device.management_phone == MANAGEMENT_PHONE

    def test_adoption_happens_once(self, ingest: IngestService, now: datetime) -> None:
        """두 번째 프레임이 기기를 또 만들면 같은 노드가 둘로 갈라진다."""
        unknown = replace(_frame(1, AlertState.NORMAL, now), hw_id=DeviceId("112233445566"))
        first = ingest.ingest(unknown, _raw(now))

        second = ingest.ingest(
            replace(unknown, seq=2, measured_at=now + timedelta(seconds=1)),
            _raw(now + timedelta(seconds=1)),
        )

        assert second.device.id == first.device.id


class TestIdempotency:
    def test_duplicate_frame_is_not_stored_twice(
        self, ingest: IngestService, registered: Device, now: datetime
    ) -> None:
        frame = _frame(1, AlertState.NORMAL, now)
        ingest.ingest(frame, _raw(now))

        second = ingest.ingest(frame, _raw(now))

        assert second.duplicate is True
        assert second.alert is None

    def test_missed_frames_are_counted(
        self, ingest: IngestService, registered: Device, now: datetime
    ) -> None:
        ingest.ingest(_frame(1, AlertState.NORMAL, now), _raw(now))

        outcome = ingest.ingest(
            _frame(5, AlertState.NORMAL, now + timedelta(minutes=5)),
            _raw(now + timedelta(minutes=5)),
        )

        assert outcome.missed_frames == 3


class TestTransition:
    def test_alert_points_at_the_reading_that_caused_it(
        self, ingest: IngestService, session: Session, registered: Device, now: datetime
    ) -> None:
        """이 링크가 비면 경보의 근거가 된 측정값을 DB에서 되짚을 수 없다."""
        ingest.ingest(_frame(1, AlertState.NORMAL, now), _raw(now))

        outcome = ingest.ingest(
            _frame(2, AlertState.ALARM, now + timedelta(minutes=1)),
            _raw(now + timedelta(minutes=1)),
        )

        assert outcome.alert is not None
        assert outcome.alert.reading_id == outcome.reading.key
        stored = SqlAlchemyAlertRepository(session).get(outcome.alert.key)
        assert stored is not None
        assert stored.reading_id == outcome.reading.key

    def test_same_state_creates_no_alert(
        self, ingest: IngestService, registered: Device, now: datetime
    ) -> None:
        """heartbeat마다 알람이 나가면 안 된다."""
        ingest.ingest(_frame(1, AlertState.NORMAL, now), _raw(now))

        outcome = ingest.ingest(
            _frame(2, AlertState.NORMAL, now + timedelta(minutes=5)),
            _raw(now + timedelta(minutes=5)),
        )

        assert outcome.alert is None

    def test_state_change_creates_alert_and_event(
        self, ingest: IngestService, session: Session, registered: Device, now: datetime
    ) -> None:
        ingest.ingest(_frame(1, AlertState.NORMAL, now), _raw(now))

        outcome = ingest.ingest(
            _frame(2, AlertState.ALARM, now + timedelta(minutes=1)),
            _raw(now + timedelta(minutes=1)),
        )

        assert outcome.alert is not None
        assert outcome.alert.to_state is AlertState.ALARM
        assert outcome.needs_dispatch is True
        events = SqlAlchemyEventRepository(session).list_in_period(
            registered.key, Period(now - timedelta(hours=1), now + timedelta(hours=1)), limit=10
        )
        assert events[0].description == "정상 → 경보 전환"

    def test_first_ever_frame_creates_no_alert(
        self, ingest: IngestService, registered: Device, now: datetime
    ) -> None:
        """직전 상태를 모르면 '전이'가 아니다."""
        outcome = ingest.ingest(_frame(1, AlertState.ALARM, now), _raw(now))

        assert outcome.alert is None

    def test_normal_transition_does_not_dispatch(
        self, ingest: IngestService, registered: Device, now: datetime
    ) -> None:
        ingest.ingest(_frame(1, AlertState.WATCH, now), _raw(now))

        outcome = ingest.ingest(
            _frame(2, AlertState.NORMAL, now + timedelta(minutes=1)),
            _raw(now + timedelta(minutes=1)),
        )

        assert outcome.alert is not None
        assert outcome.needs_dispatch is False


class TestDerivedSlope:
    """노드가 기울기를 안 보내므로 서버가 직전 관측과 견줘 채운다."""

    def _rising(self, at: datetime, co: float) -> TelemetryFrame:
        return replace(
            _frame(1, AlertState.NORMAL, at),
            values={Measure.CO_DEV: co},
        )

    def test_first_frame_stores_no_slope(
        self, ingest: IngestService, session: Session, registered: Device, now: datetime
    ) -> None:
        ingest.ingest(self._rising(now, 100.0), _raw(now))

        stored = SqlAlchemyReadingRepository(session).latest(registered.key)

        assert stored is not None
        assert stored.value(Measure.CO_SLOPE) is None

    def test_second_frame_stores_the_rate_since_the_first(
        self, ingest: IngestService, session: Session, registered: Device, now: datetime
    ) -> None:
        later = now + timedelta(seconds=30)
        ingest.ingest(self._rising(now, 100.0), _raw(now))
        ingest.ingest(self._rising(later, 160.0), _raw(later))

        stored = SqlAlchemyReadingRepository(session).latest(registered.key)

        assert stored is not None
        assert stored.value(Measure.CO_SLOPE) == pytest.approx(120.0)

    def test_the_rate_survives_the_round_trip_into_the_channel_view(
        self, ingest: IngestService, session: Session, registered: Device, now: datetime
    ) -> None:
        """앱이 읽는 것은 channel(value, slope)다 — 컬럼에 남아야 거기까지 간다."""
        later = now + timedelta(minutes=1)
        ingest.ingest(self._rising(now, 100.0), _raw(now))
        ingest.ingest(self._rising(later, 130.0), _raw(later))

        stored = SqlAlchemyReadingRepository(session).latest(registered.key)

        assert stored is not None
        channel = stored.channel(GasChannel.CO)
        assert channel is not None
        assert channel.deviation == pytest.approx(130.0)
        assert channel.slope == pytest.approx(30.0)

    def test_a_gap_past_the_window_leaves_the_slope_empty(
        self, ingest: IngestService, session: Session, registered: Device, now: datetime
    ) -> None:
        stale = now + timedelta(minutes=30)
        ingest.ingest(self._rising(now, 100.0), _raw(now))
        ingest.ingest(self._rising(stale, 900.0), _raw(stale))

        stored = SqlAlchemyReadingRepository(session).latest(registered.key)

        assert stored is not None
        assert stored.value(Measure.CO_SLOPE) is None


class TestStoredFields:
    def test_radio_quality_is_recorded(
        self, ingest: IngestService, session: Session, registered: Device, now: datetime
    ) -> None:
        """RSSI·SNR은 유실 원인 추적의 유일한 지표다."""
        ingest.ingest(_frame(1, AlertState.NORMAL, now), _raw(now))

        stored = SqlAlchemyReadingRepository(session).latest(registered.key)

        assert stored is not None
        assert stored.radio.rssi == -74
        assert stored.radio.snr == pytest.approx(7.5)

    def test_node_and_server_times_are_both_kept(
        self, ingest: IngestService, session: Session, registered: Device, now: datetime
    ) -> None:
        received = now + timedelta(seconds=42)
        ingest.ingest(_frame(1, AlertState.NORMAL, now), _raw(received))

        stored = SqlAlchemyReadingRepository(session).latest(registered.key)

        assert stored is not None
        assert stored.measured_at == now
        assert stored.received_at == received
