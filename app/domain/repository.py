"""저장소 port. 시그니처에 domain 타입만 등장한다 — Session·ORM 노출 금지."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from app.domain.models import Alert, Device, Reading
from app.domain.value_objects import DeviceId


class DeviceRepository(Protocol):
    def get_by_hw_id(self, hw_id: DeviceId) -> Device | None: ...

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
