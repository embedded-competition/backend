"""API 테스트 공용 fixture."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session

from tests.integration.api.client import RegisteredDevice, register, row_id


@pytest.fixture
async def device(client: AsyncClient) -> RegisteredDevice:
    """등록을 마친 기기. 대부분의 엔드포인트가 등록을 전제한다."""
    return await register(client)


@pytest.fixture
def device_id(session: Session, device: RegisteredDevice) -> int:
    """테스트가 직접 행을 심을 때 쓰는 내부 PK."""
    return row_id(session, device)
