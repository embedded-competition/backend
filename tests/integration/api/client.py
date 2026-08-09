"""API 테스트용 클라이언트 래퍼.

앱 spec의 인증 요청은 전부 `/devices/{deviceId}/...` + Bearer 형태다. 그 조립을
매 테스트가 반복하면 URL 규칙이 바뀔 때 전 테스트를 고쳐야 한다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from httpx import AsyncClient, Response
from sqlalchemy.orm import Session

from app.infrastructure.db.repositories.devices import SqlAlchemyDeviceRepository

MAC = "AA:BB:CC:DD:EE:FF"
OTHER_MAC = "11:22:33:44:55:66"


@dataclass(frozen=True, slots=True)
class RegisteredDevice:
    client: AsyncClient
    public_id: str
    token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}

    async def get(self, path: str, **kwargs: Any) -> Response:
        return await self.client.get(self._url(path), headers=self.headers, **kwargs)

    async def post(self, path: str, **kwargs: Any) -> Response:
        return await self.client.post(self._url(path), headers=self.headers, **kwargs)

    def _url(self, path: str) -> str:
        return f"/devices/{self.public_id}/{path}"


async def register(client: AsyncClient, mac: str = MAC) -> RegisteredDevice:
    response = await client.post("/devices", json={"mac": mac})
    assert response.status_code == 201, response.text
    body = response.json()
    return RegisteredDevice(client=client, public_id=body["deviceId"], token=body["deviceToken"])


def row_id(session: Session, device: RegisteredDevice) -> int:
    """앱에 노출되는 public_id를 내부 FK로 바꾼다 (D8)."""
    found = SqlAlchemyDeviceRepository(session).get_by_public_id(device.public_id)
    assert found is not None
    assert found.id is not None
    return found.id
