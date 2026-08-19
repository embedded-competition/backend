"""수신 기록 저장소 통합 테스트. wide 컬럼 왕복이 핵심이다."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from app.domain.frames import Coordinates
from app.domain.measurements import Measure
from app.domain.value_objects import (
    AlertState,
    Condition,
    GasChannel,
    Interval,
    Period,
    SignatureFlags,
)
from app.infrastructure.db.repositories.readings import SqlAlchemyReadingRepository
from tests.builders import a_frame, a_reading


class TestIdempotentInsert:
    def test_stored_reading_carries_its_key(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        """이 값이 없으면 이 기록을 가리키는 FK(alerts.reading_id)가 전부 빈다."""
        stored = readings.add_if_absent(a_reading(now, device_id=device_id))

        assert stored is not None
        assert stored.key > 0

    def test_duplicate_frame_is_ignored(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        """LoRa 재전송 멱등 — 같은 (device, measured_at, seq)는 한 번만 저장."""
        reading = a_reading(now, device_id=device_id)
        readings.add_if_absent(reading)

        assert readings.add_if_absent(reading) is None
        assert readings.latest(device_id) is not None


class TestValueRoundTrip:
    def test_channels_roundtrip_through_wide_columns(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        readings.add_if_absent(
            a_reading(
                now,
                device_id=device_id,
                frame=a_frame(
                    now,
                    values={
                        Measure.VOC_DEV: 6.2,
                        Measure.VOC_SLOPE: 7.1,
                        Measure.H2_DEV: 1.0,
                    },
                ),
            )
        )

        stored = readings.latest(device_id)

        assert stored is not None
        voc = stored.channel(GasChannel.VOC)
        assert voc is not None
        assert voc.deviation == pytest.approx(6.2)
        assert voc.slope == pytest.approx(7.1)
        # 값이 하나도 없는 채널은 도메인에 올리지 않는다 (미장착 센서와 구분)
        assert stored.channel(GasChannel.CO) is None

    def test_timestamps_survive_as_aware_utc(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        """SQLite에 tz 타입이 없어 naive로 돌아오는 함정을 UtcDateTime이 막는다."""
        readings.add_if_absent(a_reading(now, device_id=device_id))

        stored = readings.latest(device_id)

        assert stored is not None
        assert stored.measured_at.tzinfo is not None
        assert stored.measured_at == now

    def test_signature_roundtrip(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        readings.add_if_absent(
            a_reading(
                now,
                device_id=device_id,
                frame=a_frame(
                    now,
                    signature=SignatureFlags(rise=True, hold=False, no_recover=True, hold_s=18),
                ),
            )
        )

        stored = readings.latest(device_id)

        assert stored is not None
        assert stored.frame.signature is not None
        assert stored.frame.signature.hold_s == 18
        # 3요소가 각각 왕복해야 한다 — 하나로 뭉치면 어느 게 빠졌는지 잃는다
        assert stored.frame.signature.rise is True
        assert stored.frame.signature.hold is False
        assert stored.frame.signature.no_recover is True

    def test_signature_absent_stays_none(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        """노드가 signature를 안 보낸 경우와 '전부 false'를 구분해야 한다."""
        readings.add_if_absent(a_reading(now, device_id=device_id))

        stored = readings.latest(device_id)

        assert stored is not None
        assert stored.frame.signature is None

    def test_gps_and_batt_roundtrip(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        readings.add_if_absent(
            a_reading(
                now,
                device_id=device_id,
                frame=a_frame(now, location=Coordinates(lat=37.5573, lon=127.0329), batt_mv=3960),
            )
        )

        stored = readings.latest(device_id)

        assert stored is not None
        assert stored.frame.location is not None
        assert stored.frame.location.lat == pytest.approx(37.5573)
        assert stored.frame.batt_mv == 3960

    def test_gps_missing_is_null_not_zero(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        """GPS 미장착(정합화 C2)을 좌표 0,0으로 뭉개지 않는다."""
        readings.add_if_absent(a_reading(now, device_id=device_id))

        stored = readings.latest(device_id)

        assert stored is not None
        assert stored.frame.location is None

    def test_conditions_roundtrip(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        readings.add_if_absent(
            a_reading(
                now,
                device_id=device_id,
                frame=a_frame(now, conditions=frozenset({Condition.CO_RISE, Condition.WATER})),
            )
        )

        stored = readings.latest(device_id)

        assert stored is not None
        assert stored.conditions == frozenset({Condition.CO_RISE, Condition.WATER})

    def test_conditions_default_to_empty_when_absent(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        """프레임은 항상 실제 값(빈 집합 포함)을 싣는다 — NULL은 과거 미마이그레이션 행의 몫."""
        readings.add_if_absent(a_reading(now, device_id=device_id))

        stored = readings.latest(device_id)

        assert stored is not None
        assert stored.conditions == frozenset()


class TestBucketMaxima:
    def test_same_hour_on_different_days_stays_apart(
        self, readings: SqlAlchemyReadingRepository, device_id: int
    ) -> None:
        """시각만으로 묶으면 8/4 14시와 8/7 14시가 한 칸으로 합쳐진다."""
        first = datetime(2026, 8, 4, 14, 0, tzinfo=UTC)
        third = datetime(2026, 8, 7, 14, 0, tzinfo=UTC)
        _store(readings, device_id, first, seq=1, voc_dev=1.0)
        _store(readings, device_id, third, seq=2, voc_dev=9.0)

        buckets = readings.bucket_maxima(
            device_id,
            Period(datetime(2026, 8, 4, tzinfo=UTC), datetime(2026, 8, 8, tzinfo=UTC)),
            Interval.H1,
        )

        assert len(buckets) == 2
        assert [b.value(Measure.VOC_DEV) for b in buckets] == [1.0, 9.0]
        assert buckets[0].start == first
        assert buckets[1].start == third

    def test_takes_maximum_not_mean(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        """평균은 스파이크를 지운다 — 지워진 스파이크가 곧 놓친 경보다."""
        for index, value in enumerate([0.0, 8.0, 0.0]):
            _store(readings, device_id, now + timedelta(minutes=index), seq=index, voc_dev=value)

        buckets = readings.bucket_maxima(
            device_id, Period(now, now + timedelta(hours=1)), Interval.H1
        )

        assert len(buckets) == 1
        assert buckets[0].value(Measure.VOC_DEV) == pytest.approx(8.0)
        assert buckets[0].samples == 3

    def test_worst_state_wins_inside_a_bucket(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        for index, state in enumerate([AlertState.NORMAL, AlertState.ALARM, AlertState.WATCH]):
            _store(readings, device_id, now + timedelta(minutes=index), seq=index, state=state)

        buckets = readings.bucket_maxima(
            device_id, Period(now, now + timedelta(hours=1)), Interval.H1
        )

        assert buckets[0].state is AlertState.ALARM

    def test_gaps_are_omitted_not_zero_filled(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        _store(readings, device_id, now, seq=1, voc_dev=1.0)
        _store(readings, device_id, now + timedelta(hours=3), seq=2, voc_dev=2.0)

        period = Period(now, now + timedelta(hours=4))
        buckets = readings.bucket_maxima(device_id, period, Interval.H1)

        assert [b.start for b in buckets] == [now, now + timedelta(hours=3)]

    def test_reads_beyond_the_old_two_thousand_row_cap(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        """예전 구현은 최근 2000행만 읽어 앞쪽 날짜를 조용히 비웠다."""
        for index in range(2_100):
            _store(readings, device_id, now + timedelta(seconds=index), seq=index, voc_dev=1.0)
        _store(readings, device_id, now, seq=99_999, voc_dev=7.0)

        buckets = readings.bucket_maxima(
            device_id, Period(now, now + timedelta(hours=1)), Interval.H1
        )

        assert buckets[0].samples == 2_101
        assert buckets[0].value(Measure.VOC_DEV) == pytest.approx(7.0)


class TestMeasurePeak:
    def test_reports_value_and_when_it_happened(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        peak_at = now + timedelta(minutes=2)
        _store(readings, device_id, now, seq=1, voc_dev=1.0)
        _store(readings, device_id, peak_at, seq=2, voc_dev=8.1, state=AlertState.WATCH)
        _store(readings, device_id, now + timedelta(minutes=4), seq=3, voc_dev=0.5)

        peak = readings.measure_peak(
            device_id,
            Period(now, now + timedelta(hours=1)),
            Measure.VOC_DEV,
            Measure.VOC_SLOPE,
        )

        assert peak is not None
        assert peak.value == pytest.approx(8.1)
        assert peak.at == peak_at

    def test_channel_without_any_value_has_no_peak(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        _store(readings, device_id, now, seq=1, voc_dev=1.0)

        assert (
            readings.measure_peak(
                device_id,
                Period(now, now + timedelta(hours=1)),
                Measure.CO_DEV,
                Measure.CO_SLOPE,
            )
            is None
        )


class TestPeriodExtremes:
    def test_returns_none_when_period_is_empty(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        assert readings.period_extremes(device_id, Period(now, now + timedelta(hours=1))) is None

    def test_end_is_excluded(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        _store(readings, device_id, now + timedelta(hours=1), seq=1, state=AlertState.ALARM)

        assert readings.period_extremes(device_id, Period(now, now + timedelta(hours=1))) is None

    def test_reports_worst_state_and_last_observation(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        last_at = now + timedelta(minutes=5)
        _store(readings, device_id, now, seq=1, voc_dev=1.0, state=AlertState.ALARM)
        _store(readings, device_id, last_at, seq=2, voc_dev=2.0, state=AlertState.NORMAL)

        extremes = readings.period_extremes(device_id, Period(now, now + timedelta(hours=1)))

        assert extremes is not None
        assert extremes.state is AlertState.ALARM
        assert extremes.at == last_at
        assert extremes.value(Measure.VOC_DEV) == pytest.approx(2.0)


class TestLatestLocated:
    def test_skips_frames_without_coordinates(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        _store(readings, device_id, now, seq=1, voc_dev=1.0, location=Coordinates(37.5, 127.0))
        _store(readings, device_id, now + timedelta(minutes=1), seq=2, voc_dev=1.0)

        found = readings.latest_located(device_id)

        assert found is not None
        assert found.frame.location == Coordinates(37.5, 127.0)

    def test_returns_none_when_no_frame_carried_coordinates(
        self, readings: SqlAlchemyReadingRepository, device_id: int, now: datetime
    ) -> None:
        _store(readings, device_id, now, seq=1, voc_dev=1.0)

        assert readings.latest_located(device_id) is None


def _store(
    readings: SqlAlchemyReadingRepository,
    device_id: int,
    at: datetime,
    *,
    seq: int,
    voc_dev: float | None = None,
    state: AlertState = AlertState.NORMAL,
    location: Coordinates | None = None,
) -> None:
    values = {} if voc_dev is None else {Measure.VOC_DEV: voc_dev}
    readings.add_if_absent(
        a_reading(
            at,
            device_id=device_id,
            frame=a_frame(at, seq=seq, state=state, values=values, location=location),
        )
    )
