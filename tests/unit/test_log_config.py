"""로깅 설정 단위 테스트.

`extra=`로 실은 필드가 포맷터에서 버려지면 구조화 로그가 이름만 남는다 —
운영에서 rssi·code·attempted 같은 값이 사라지는 경로다.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

import pytest

from app.core.config import Settings
from app.runtime.log_config import (
    HANDLER_NAME,
    JsonFormatter,
    TextFormatter,
    configure_logging,
)


def _record(**extra: Any) -> logging.LogRecord:
    record = logging.LogRecord(
        name="app.runtime.receiver",
        level=logging.INFO,
        pathname="receiver.py",
        lineno=91,
        msg="alert dispatched",
        args=None,
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def _settings(tmp_path: Path, **overrides: Any) -> Settings:
    return Settings(environment="local", database_path=tmp_path / "unused.db", **overrides)


class TestJsonFormatter:
    def test_extra_fields_survive(self) -> None:
        line = JsonFormatter().format(_record(attempted=2, delivered=2, deactivated=0))

        payload = json.loads(line)
        assert payload["message"] == "alert dispatched"
        assert payload["logger"] == "app.runtime.receiver"
        assert payload["level"] == "INFO"
        assert (payload["attempted"], payload["delivered"], payload["deactivated"]) == (2, 2, 0)

    def test_timestamp_is_utc_iso8601(self) -> None:
        payload = json.loads(JsonFormatter().format(_record()))

        assert payload["ts"].endswith("Z")

    def test_korean_is_not_escaped(self) -> None:
        line = JsonFormatter().format(_record(detail="수신 task 미가동"))

        assert "수신 task 미가동" in line

    def test_unserializable_value_does_not_break_the_line(self) -> None:
        payload = json.loads(JsonFormatter().format(_record(payload=object())))

        assert "payload" in payload

    def test_exception_is_included(self) -> None:
        try:
            raise ValueError("boom")
        except ValueError:
            record = _record()
            record.exc_info = sys.exc_info()

        payload = json.loads(JsonFormatter().format(record))

        assert "ValueError: boom" in payload["exception"]


class TestTextFormatter:
    def test_extra_fields_are_appended(self) -> None:
        line = TextFormatter().format(_record(attempted=2, delivered=2))

        assert "alert dispatched" in line
        assert "attempted=2" in line
        assert "delivered=2" in line

    def test_record_without_extra_has_no_trailing_space(self) -> None:
        line = TextFormatter().format(_record())

        assert line == line.rstrip()


class TestConfigureLogging:
    @pytest.fixture(autouse=True)
    def _restore_root(self) -> Any:
        root = logging.getLogger()
        handlers, level = list(root.handlers), root.level
        app_level = logging.getLogger("app").level
        yield
        root.handlers[:] = handlers
        root.setLevel(level)
        logging.getLogger("app").setLevel(app_level)

    def test_is_idempotent(self, tmp_path: Path) -> None:
        """앱 팩토리는 테스트마다 다시 불린다 — 핸들러가 쌓이면 로그가 중복된다."""
        configure_logging(_settings(tmp_path))
        configure_logging(_settings(tmp_path))

        root = logging.getLogger()
        assert len([h for h in root.handlers if h.get_name() == HANDLER_NAME]) == 1

    def test_app_level_follows_settings(self, tmp_path: Path) -> None:
        configure_logging(_settings(tmp_path, log_level="DEBUG"))

        assert logging.getLogger("app").level == logging.DEBUG

    def test_third_party_stays_quiet(self, tmp_path: Path) -> None:
        """app만 INFO로 연다. root까지 열면 sqlalchemy가 SD카드를 채운다."""
        configure_logging(_settings(tmp_path, log_level="INFO"))

        assert logging.getLogger("sqlalchemy.engine").getEffectiveLevel() == logging.WARNING
        assert logging.getLogger("app.runtime.receiver").getEffectiveLevel() == logging.INFO

    def test_format_choice_is_applied(self, tmp_path: Path) -> None:
        configure_logging(_settings(tmp_path, log_format="json"))
        root = logging.getLogger()
        handler = next(h for h in root.handlers if h.get_name() == HANDLER_NAME)

        assert isinstance(handler.formatter, JsonFormatter)

    def test_uvicorn_loggers_are_adopted(self, tmp_path: Path) -> None:
        """uvicorn이 자기 핸들러를 물고 있으면 접근 로그만 포맷이 달라진다."""
        access = logging.getLogger("uvicorn.access")
        access.addHandler(logging.NullHandler())
        access.propagate = False

        configure_logging(_settings(tmp_path))

        assert access.handlers == []
        assert access.propagate is True
