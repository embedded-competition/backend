"""수신 기록 단위 테스트. 외부 의존 0."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.domain.measurements import Measure
from app.domain.readings import RadioQuality
from app.domain.value_objects import GasChannel
from tests.builders import a_frame, a_reading


class TestValidation:
    def test_naive_datetime_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            # naive datetime이 이 테스트의 입력이다.
            a_reading(datetime(2026, 8, 8, 12, 0, 0))  # noqa: DTZ001

    @pytest.mark.parametrize("humidity", [-1.0, 100.1])
    def test_humidity_out_of_range_is_rejected(self, now: datetime, humidity: float) -> None:
        """범위 검증이 measurements 표 한 곳에서 나온다."""
        with pytest.raises(ValueError, match="humidity_pct"):
            a_reading(now, frame=a_frame(now, values={Measure.HUMIDITY_PCT: humidity}))

    def test_positive_rssi_is_rejected(self, now: datetime) -> None:
        with pytest.raises(ValueError, match="rssi"):
            a_reading(now, radio=RadioQuality(rssi=3))


class TestNodeAndServerTime:
    def test_both_times_are_kept_apart(self, now: datetime) -> None:
        """노드 시각을 서버 수신 시각으로 보정하지 않는다 — 어긋남이 드러나야 한다."""
        reading = a_reading(now, received_at=now + timedelta(seconds=42))

        assert reading.measured_at == now
        assert reading.received_at == now + timedelta(seconds=42)


class TestChannelLookup:
    def test_channel_with_values(self, now: datetime) -> None:
        frame = a_frame(now, values={Measure.VOC_DEV: 6.2, Measure.VOC_SLOPE: 7.1})

        voc = a_reading(now, frame=frame).channel(GasChannel.VOC)

        assert voc is not None
        assert voc.deviation == pytest.approx(6.2)

    def test_channel_without_values_is_none(self, now: datetime) -> None:
        """값이 없는 채널은 올라오지 않는다 — 미장착 센서와 구분한다."""
        assert a_reading(now).channel(GasChannel.CO) is None
