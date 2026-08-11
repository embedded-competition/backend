"""노드가 지금 실제로 보내는 CSV 파싱.

프레임 v2 전환 전까지만 쓰는 임시 경로다. 노드는 기기 식별자도 seq도 시각도
보내지 않으므로 서버가 채운다 — 무엇을 서버가 지어냈는지 여기서 못박아 둔다.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.domain.exceptions import FrameFieldError
from app.domain.measurements import Measure
from app.domain.value_objects import AlertState
from app.infrastructure.lora.node_csv import NodeCsvParser

_LINE = b"MQ7=1234,MQ8=987,SGP=30000,FSR=100,WATER=50,ALERT=NONE"
_AT = datetime(2026, 8, 11, 7, 0, tzinfo=UTC)


def _parser() -> NodeCsvParser:
    return NodeCsvParser("aabbccddeeff")


class TestValues:
    def test_each_sensor_lands_in_its_channel(self) -> None:
        frame = _parser().parse(_LINE, _AT)

        assert frame.value(Measure.CO_DEV) == 1234.0
        assert frame.value(Measure.H2_DEV) == 987.0
        assert frame.value(Measure.VOC_DEV) == 30000.0
        assert frame.value(Measure.PRESSURE_DEV) == 100.0

    def test_unmapped_keys_are_dropped(self) -> None:
        """WATER 원시 수위는 대응할 자리가 없다. 지어내지 않고 버린다."""
        frame = _parser().parse(_LINE, _AT)

        assert Measure.TEMP_C not in frame.values
        assert len(frame.values) == 4

    def test_measured_at_comes_from_the_server(self) -> None:
        """노드에 시계가 없다. 수신 시각이 유일한 시각이다."""
        assert _parser().parse(_LINE, _AT).measured_at == _AT

    def test_seq_increases_per_frame(self) -> None:
        parser = _parser()

        first = parser.parse(_LINE, _AT)
        second = parser.parse(_LINE, _AT)

        assert (first.seq, second.seq) == (1, 2)


class TestState:
    def test_none_is_normal(self) -> None:
        assert _parser().parse(_LINE, _AT).state is AlertState.NORMAL

    def test_any_cause_is_watch(self) -> None:
        line = b"MQ7=1,MQ8=1,SGP=1,FSR=1,WATER=1,ALERT=MQ7|SGP40"

        assert _parser().parse(line, _AT).state is AlertState.WATCH

    def test_saturation_alone_is_fault(self) -> None:
        """포화된 센서는 위험이 아니라 못 믿는 상태다."""
        line = b"MQ7=4095,MQ8=4095,SGP=1,FSR=1,WATER=1,ALERT=MQ7_SATURATED|MQ8_SATURATED"

        assert _parser().parse(line, _AT).state is AlertState.FAULT

    def test_water_alert_sets_the_flag(self) -> None:
        line = b"MQ7=1,MQ8=1,SGP=1,FSR=1,WATER=900,ALERT=WATER_LEVEL"
        frame = _parser().parse(line, _AT)

        assert frame.water is True
        assert frame.state is AlertState.WATCH


class TestMalformed:
    def test_garbage_is_rejected(self) -> None:
        with pytest.raises(FrameFieldError):
            _parser().parse(b"", _AT)

    def test_non_numeric_value_names_the_key(self) -> None:
        with pytest.raises(FrameFieldError, match="MQ7"):
            _parser().parse(b"MQ7=abc,ALERT=NONE", _AT)

    def test_missing_sensor_does_not_fail_the_frame(self) -> None:
        """센서 하나가 빠져도 나머지는 기록한다."""
        frame = _parser().parse(b"MQ7=10,ALERT=NONE", _AT)

        assert frame.value(Measure.CO_DEV) == 10.0
        assert frame.value(Measure.H2_DEV) is None
