"""저장 식별자 단위 테스트.

`id or 0`으로 뭉개던 자리를 대체한다 — 없는 식별자는 조용히 0이 되지 않고 터진다.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from app.domain.exceptions import DomainError
from app.domain.stored import NotStored
from tests.builders import a_device, a_reading, an_alert


class TestUnsavedObjectsHaveNoKey:
    def test_device(self) -> None:
        with pytest.raises(NotStored, match="device"):
            _ = a_device().key

    def test_alert(self, now: datetime) -> None:
        with pytest.raises(NotStored, match="alert"):
            _ = an_alert(now).key

    def test_reading(self, now: datetime) -> None:
        with pytest.raises(NotStored, match="reading"):
            _ = a_reading(now).key


class TestSavedObjectsExposeKey:
    def test_device(self) -> None:
        assert a_device(key=7).key == 7

    def test_not_stored_is_not_a_domain_error(self) -> None:
        """업무 위반이 아니라 호출 순서 결함 — 400으로 앱에 내려가면 안 된다."""
        assert not issubclass(NotStored, DomainError)
