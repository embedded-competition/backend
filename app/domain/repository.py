"""저장소 port. 시그니처에 domain 타입만 등장한다 — Session·ORM 노출 금지."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.domain.models import AccessToken, Alert, Device, Event, PushToken, Reading
from app.domain.value_objects import DeviceId


class DeviceRepository(Protocol):
    def get_by_hw_id(self, hw_id: DeviceId) -> Device | None: ...

    def get_by_mac(self, mac: str) -> Device | None:
        """앱 등록 키로 조회. 중복 등록 판정에 쓴다."""
        ...

    def get_by_public_id(self, public_id: str) -> Device | None:
        """앱이 URL에 쓰는 식별자로 조회 (D8)."""
        ...

    def get(self, device_id: int) -> Device | None: ...

    def list_active(self) -> list[Device]: ...

    def save(self, device: Device) -> Device: ...


class ReadingRepository(Protocol):
    def add_if_absent(self, reading: Reading) -> bool:
        """멱등 삽입. 이미 있으면 False (LoRa 재전송 중복)."""
        ...

    def list_in_range(
        self,
        device_id: int,
        *,
        start: datetime,
        end: datetime,
        limit: int,
    ) -> list[Reading]:
        """시간 범위와 상한을 항상 요구한다 — 무제한 조회는 RPi에서 OOM 경로."""
        ...

    def latest(self, device_id: int) -> Reading | None: ...


class AlertRepository(Protocol):
    def add(self, alert: Alert) -> Alert: ...

    def get(self, alert_id: int) -> Alert | None: ...

    def list_active(self) -> list[Alert]:
        """해제되지 않은 알람. 부분 인덱스가 지원한다."""
        ...

    def list_for_device(self, device_id: int, *, limit: int) -> list[Alert]: ...

    def save(self, alert: Alert) -> Alert: ...


class EventRepository(Protocol):
    def add(self, event: Event) -> Event: ...

    def list_since(self, device_id: int, *, since: datetime, limit: int) -> list[Event]:
        """기록 탭. 항상 시작 시각과 상한을 요구한다."""
        ...

    def list_in_range(
        self, device_id: int, *, start: datetime, end: datetime, limit: int
    ) -> list[Event]: ...


class AccessTokenRepository(Protocol):
    def add(self, token: AccessToken) -> AccessToken: ...

    def find_device_id(self, token_hash: str) -> int | None:
        """해시로 소유 기기를 찾는다. 원문은 서버에 없다."""
        ...

    def touch(self, token_hash: str, *, at: datetime) -> None: ...


class PushTokenRepository(Protocol):
    def upsert(self, token: PushToken) -> PushToken:
        """멱등 등록 — 같은 토큰 재등록이 중복 행을 만들지 않는다."""
        ...

    def list_active(self, device_id: int) -> list[PushToken]: ...

    def save(self, token: PushToken) -> PushToken: ...
