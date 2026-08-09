"""기기 애그리게이트 단위 테스트. 외부 의존 0."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.domain.value_objects import AlertState
from tests.builders import a_device


class TestOfflineJudgement:
    def test_never_seen_device_is_offline(self, now: datetime) -> None:
        assert a_device().is_offline(now=now, threshold_s=900) is True

    def test_recently_seen_device_is_online(self, now: datetime) -> None:
        device = a_device(last_seen_at=now - timedelta(seconds=60))

        assert device.is_offline(now=now, threshold_s=900) is False


class TestMissedFrames:
    @pytest.mark.parametrize(
        ("last_seq", "incoming", "expected"),
        [(None, 10, 0), (9, 10, 0), (5, 10, 4), (10, 9, 0)],
    )
    def test_counts_seq_gap(self, last_seq: int | None, incoming: int, expected: int) -> None:
        assert a_device(last_seq=last_seq).missed_frames_since(incoming) == expected


class TestObserve:
    def test_late_arriving_frame_does_not_rewind_observation(self, now: datetime) -> None:
        device = a_device(last_seen_at=now, last_seq=20, last_state=AlertState.ALARM)

        device.observe(seq=5, at=now - timedelta(minutes=10), state=AlertState.NORMAL)

        assert device.last_seq == 20
        assert device.last_state is AlertState.ALARM

    def test_naive_datetime_is_rejected(self, now: datetime) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            a_device().observe(seq=1, at=datetime(2026, 8, 8, 12, 0, 0), state=AlertState.NORMAL)

    def test_blank_label_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="label"):
            a_device(label="   ")
