"""domain 계층 단위 테스트. 외부 의존 0."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.domain.exceptions import AlertAlreadyAcknowledged
from app.domain.models import Alert, Device, Reading
from app.domain.value_objects import AlertState, ChannelReading, DeviceId, GasChannel


def _device(**kwargs: object) -> Device:
    defaults: dict[str, object] = {
        "public_id": "dev_test0001",
        "mac": "44:BD:8D:23:9C:28",
        "hw_id": DeviceId("44bd8d239c28"),
        "label": "1호차",
    }
    defaults.update(kwargs)
    return Device(**defaults)  # type: ignore[arg-type]


def _reading(now: datetime, **kwargs: object) -> Reading:
    defaults: dict[str, object] = {
        "device_id": 1,
        "seq": 10,
        "measured_at": now,
        "received_at": now,
        "frame_version": 1,
        "state": AlertState.NORMAL,
    }
    defaults.update(kwargs)
    return Reading(**defaults)  # type: ignore[arg-type]


class TestDeviceId:
    def test_empty_hw_id_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="비어 있을 수 없다"):
            DeviceId("")


class TestDevice:
    def test_never_seen_device_is_offline(self, now: datetime) -> None:
        assert _device().is_offline(now=now, threshold_s=900) is True

    def test_recently_seen_device_is_online(self, now: datetime) -> None:
        device = _device(last_seen_at=now - timedelta(seconds=60))
        assert device.is_offline(now=now, threshold_s=900) is False

    @pytest.mark.parametrize(
        ("last_seq", "incoming", "expected"),
        [(None, 10, 0), (9, 10, 0), (5, 10, 4), (10, 9, 0)],
    )
    def test_missed_frames_counts_seq_gap(
        self, last_seq: int | None, incoming: int, expected: int
    ) -> None:
        assert _device(last_seq=last_seq).missed_frames_since(incoming) == expected

    def test_late_arriving_frame_does_not_rewind_observation(self, now: datetime) -> None:
        device = _device(last_seen_at=now, last_seq=20, last_state=AlertState.ALARM)

        device.observe(seq=5, at=now - timedelta(minutes=10), state=AlertState.NORMAL)

        assert device.last_seq == 20
        assert device.last_state is AlertState.ALARM


class TestReading:
    def test_naive_datetime_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            _reading(datetime(2026, 8, 8, 12, 0, 0))

    @pytest.mark.parametrize("humidity", [-1.0, 100.1])
    def test_humidity_out_of_range_is_rejected(self, now: datetime, humidity: float) -> None:
        with pytest.raises(ValueError, match="humidity_pct"):
            _reading(now, humidity_pct=humidity)

    def test_positive_rssi_is_rejected(self, now: datetime) -> None:
        with pytest.raises(ValueError, match="rssi"):
            _reading(now, rssi=3)

    def test_clock_skew_is_exposed_not_corrected(self, now: datetime) -> None:
        reading = _reading(now, received_at=now + timedelta(seconds=42))

        assert reading.clock_skew_s == 42.0
        assert reading.measured_at == now  # 보정하지 않는다

    def test_channel_lookup(self, now: datetime) -> None:
        voc = ChannelReading(channel=GasChannel.VOC, deviation=6.2, slope=7.1)
        reading = _reading(now, channels=(voc,))

        assert reading.channel(GasChannel.VOC) is voc
        assert reading.channel(GasChannel.CO) is None


class TestAlert:
    def test_non_transition_is_rejected(self, now: datetime) -> None:
        with pytest.raises(ValueError, match="전이가 아닌"):
            Alert(
                device_id=1,
                from_state=AlertState.NORMAL,
                to_state=AlertState.NORMAL,
                occurred_at=now,
                detected_at=now,
            )

    def test_acknowledge_marks_inactive(self, now: datetime) -> None:
        alert = Alert(
            device_id=1,
            from_state=AlertState.WATCH,
            to_state=AlertState.ALARM,
            occurred_at=now,
            detected_at=now,
        )
        assert alert.is_active is True

        alert.acknowledge(at=now + timedelta(minutes=5), note="현장 확인")

        assert alert.is_active is False
        assert alert.acknowledged_note == "현장 확인"

    def test_double_acknowledge_is_rejected(self, now: datetime) -> None:
        alert = Alert(
            device_id=1,
            from_state=AlertState.NORMAL,
            to_state=AlertState.ALARM,
            occurred_at=now,
            detected_at=now,
        )
        alert.acknowledge(at=now)

        with pytest.raises(AlertAlreadyAcknowledged):
            alert.acknowledge(at=now)


class TestAlertState:
    def test_alarm_is_not_auto_clearable(self) -> None:
        assert AlertState.ALARM.is_auto_clearable is False
        assert AlertState.WATCH.is_auto_clearable is True

    def test_co_has_no_solo_promotion_path(self) -> None:
        assert GasChannel.CO.can_promote_alone is False
        assert GasChannel.VOC.can_promote_alone is True
        assert GasChannel.H2.can_promote_alone is True
