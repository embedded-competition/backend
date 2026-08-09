"""기기 애그리게이트 단위 테스트. 외부 의존 0."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.domain.value_objects import AlertState
from tests.builders import a_device


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
            # naive datetime이 이 테스트의 입력이다 — DTZ가 잡으면 안 되는 유일한 자리.
            naive = datetime(2026, 8, 8, 12, 0, 0)  # noqa: DTZ001
            a_device().observe(seq=1, at=naive, state=AlertState.NORMAL)

    def test_blank_label_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="label"):
            a_device(label="   ")
