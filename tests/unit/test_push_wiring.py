"""푸시 어댑터 선택 단위 테스트.

발송기와 무관한 설정(예전의 FCM 자격증명 경로)이 발송 여부를 좌우하면, 운영에서
푸시를 켜려고 아무도 읽지 않는 값을 채워야 한다. 선택은 명시적이어야 한다.
"""

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.infrastructure.push.expo import ExpoPushSender, LoggingPushSender
from app.runtime.wiring import create_push_sender


def _settings(delivery: str, tmp_path: Path) -> Settings:
    return Settings(
        environment="local",
        database_path=tmp_path / "unused.db",
        push_delivery=delivery,  # type: ignore[arg-type]
    )


def test_log_delivery_never_hits_the_network(tmp_path: Path) -> None:
    sender = create_push_sender(_settings("log", tmp_path))

    assert isinstance(sender, LoggingPushSender)


def test_expo_delivery_uses_the_expo_adapter(tmp_path: Path) -> None:
    sender = create_push_sender(_settings("expo", tmp_path))

    assert isinstance(sender, ExpoPushSender)
