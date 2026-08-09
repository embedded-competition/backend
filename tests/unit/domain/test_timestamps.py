"""시각 규약. aware 강제 + UTC 정규화 둘 다가 계약이다."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.domain.timestamps import require_aware

KST = timezone(timedelta(hours=9))


class TestRequireAware:
    def test_naive_datetime_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            require_aware(datetime(2026, 8, 8, 12, 0, 0), "measured_at")  # noqa: DTZ001

    def test_offset_datetime_is_normalised_to_utc(self) -> None:
        """UTC로 바꿔 반환하는 것까지가 계약이다.

        같은 순간이면 `==`가 성립하므로 tzinfo를 직접 보지 않으면 로컬 시각으로
        바뀌어도 테스트가 통과한다 (mutation testing이 이 구멍을 드러냈다).
        """
        normalised = require_aware(datetime(2026, 8, 8, 21, 0, 0, tzinfo=KST), "measured_at")

        assert normalised.tzinfo is UTC
        assert normalised == datetime(2026, 8, 8, 12, 0, 0, tzinfo=UTC)
        assert (normalised.hour, normalised.minute) == (12, 0)

    def test_utc_datetime_passes_through(self) -> None:
        original = datetime(2026, 8, 8, 12, 0, 0, tzinfo=UTC)

        assert require_aware(original, "measured_at") == original
