"""경보·기록 단위 테스트. 외부 의존 0."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.domain.exceptions import AlertAlreadyAcknowledged
from app.domain.value_objects import AlertState, EventKind
from tests.builders import an_alert, an_event


class TestAlertInvariants:
    def test_non_transition_is_rejected(self, now: datetime) -> None:
        with pytest.raises(ValueError, match="전이가 아닌"):
            an_alert(now, from_state=AlertState.NORMAL, to_state=AlertState.NORMAL)


class TestAcknowledge:
    def test_marks_inactive(self, now: datetime) -> None:
        alert = an_alert(now, from_state=AlertState.WATCH)
        assert alert.is_active is True

        alert.acknowledge(at=now + timedelta(minutes=5), note="현장 확인")

        assert alert.is_active is False
        assert alert.acknowledged_note == "현장 확인"

    def test_double_acknowledge_is_rejected(self, now: datetime) -> None:
        alert = an_alert(now)
        alert.acknowledge(at=now)

        with pytest.raises(AlertAlreadyAcknowledged):
            alert.acknowledge(at=now)


class TestEventInvariants:
    def test_blank_description_is_rejected(self, now: datetime) -> None:
        with pytest.raises(ValueError, match="description"):
            an_event(now, description="  ")

    def test_state_change_without_alert_is_rejected(self, now: datetime) -> None:
        """기록 탭에서 상태 변경을 눌렀는데 연결된 경보가 없으면 추적이 끊긴다."""
        with pytest.raises(ValueError, match="alert_id"):
            an_event(now, kind=EventKind.STATE_CHANGE, alert_id=None)
