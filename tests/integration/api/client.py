"""API 테스트용 클라이언트 래퍼.

모든 경로가 `/devices/{mac}/...`이고 인증은 없다. 그 조립을 매 테스트가 반복하면
URL 규칙이 바뀔 때 전 테스트를 고쳐야 한다.

기기는 등록 엔드포인트가 아니라 저장소로 심는다 — 등록 경로가 사라졌고, 실제로는
첫 프레임이 기기를 만든다.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from httpx import AsyncClient, Response
from sqlalchemy.orm import Session

from app.core import identity
from app.domain.device import Device
from app.infrastructure.db.repositories.devices import SqlAlchemyDeviceRepository

MAC = "AA:BB:CC:DD:EE:FF"
OTHER_MAC = "11:22:33:44:55:66"
UNKNOWN_MAC = "99:99:99:99:99:99"
MANAGEMENT_PHONE = "01029015899"


@dataclass(frozen=True, slots=True)
class SeededDevice:
    client: AsyncClient
    mac: str
    key: int

    async def get(self, path: str, **kwargs: Any) -> Response:
        return await self.client.get(self._url(path), **kwargs)

    async def post(self, path: str, **kwargs: Any) -> Response:
        return await self.client.post(self._url(path), **kwargs)

    def _url(self, path: str) -> str:
        return f"/devices/{self.mac}/{path}"


def seed_device(session: Session, client: AsyncClient, mac: str = MAC) -> SeededDevice:
    normalized = identity.normalize_mac(mac)
    saved = SqlAlchemyDeviceRepository(session).save(
        Device(
            public_id=identity.new_public_id(),
            mac=normalized,
            label=identity.default_label(normalized),
            management_phone=MANAGEMENT_PHONE,
            registered_at=datetime.now(UTC),
        )
    )
    session.commit()
    assert saved.id is not None
    return SeededDevice(client=client, mac=mac, key=saved.id)
