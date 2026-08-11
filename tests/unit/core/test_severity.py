"""심각도 순위와 역변환. 정렬·집계·비교가 전부 이 기준을 공유한다."""

from __future__ import annotations

import pytest

from app.core.severity import severity_of, state_for
from app.domain.value_objects import AlertState


class TestSeverityOf:
    @pytest.mark.parametrize(
        ("state", "expected"),
        [
            (AlertState.WARMUP, 0),
            (AlertState.NORMAL, 0),
            (AlertState.FAULT, 1),
            (AlertState.WATCH, 2),
            (AlertState.ALARM, 3),
        ],
    )
    def test_rank(self, state: AlertState, expected: int) -> None:
        assert severity_of(state) == expected

    def test_alarm_outranks_every_other_state(self) -> None:
        others = [s for s in AlertState if s is not AlertState.ALARM]

        assert all(severity_of(AlertState.ALARM) > severity_of(s) for s in others)

    def test_fault_is_not_treated_as_normal(self) -> None:
        """감지 불능을 정상으로 뭉개면 고장난 노드가 조용해진다."""
        assert severity_of(AlertState.FAULT) > severity_of(AlertState.NORMAL)


class TestStateFor:
    @pytest.mark.parametrize(
        ("severity", "expected"),
        [
            # 경계 바로 위/아래를 둘 다 본다 — 한쪽만 보면 부등호 방향이 안 잡힌다.
            (3.0, AlertState.ALARM),
            (2.5, AlertState.ALARM),
            (2.49, AlertState.WATCH),
            (1.5, AlertState.WATCH),
            (1.49, AlertState.FAULT),
            (0.5, AlertState.FAULT),
            (0.49, AlertState.NORMAL),
            (0.0, AlertState.NORMAL),
        ],
    )
    def test_boundaries(self, severity: float, expected: AlertState) -> None:
        assert state_for(severity) == expected

    def test_round_trip_from_each_state(self) -> None:
        for state in (AlertState.NORMAL, AlertState.FAULT, AlertState.WATCH, AlertState.ALARM):
            assert state_for(float(severity_of(state))) == state


class TestStateOrdering:
    """AlertState.severity는 저장소가 SQL CASE로 옮겨 쓴다 — core와 어긋나면 버킷 상태가 틀린다."""

    def test_agrees_with_core_severity(self) -> None:
        ordered = sorted(AlertState, key=lambda state: state.severity)
        scores = [severity_of(state) for state in ordered]

        assert scores == sorted(scores)

    def test_alarm_is_the_worst(self) -> None:
        assert max(AlertState, key=lambda state: state.severity) is AlertState.ALARM

    def test_severity_round_trips(self) -> None:
        for state in AlertState:
            assert AlertState.of_severity(state.severity) is state
