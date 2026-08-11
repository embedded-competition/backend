"""API 테스트 공용 fixture."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from tests.integration.api.client import SeededDevice, seed_device


@pytest.fixture
def device(session: Session, client: AsyncClient) -> SeededDevice:
    """조회 대상 기기. MAC이 곧 경로이자 식별자다."""
    return seed_device(session, client)


@pytest.fixture
def device_id(device: SeededDevice) -> int:
    """테스트가 직접 행을 심을 때 쓰는 내부 PK."""
    return device.key
