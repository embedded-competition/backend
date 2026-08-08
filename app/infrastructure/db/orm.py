"""SQLAlchemy mapped class. 데이터 매핑 전용 — 도메인 메서드를 붙이지 않는다.

스키마 근거는 docs/db-schema.md. 변경은 Alembic 리비전이 SSOT다.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.infrastructure.db.types import UtcDateTime


class Base(DeclarativeBase):
    pass


class DeviceOrm(Base):
    """노드 1개 = 차량 1대. 차량 테이블을 따로 두지 않는다."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    hw_id: Mapped[str] = mapped_column(String(32), unique=True)
    label: Mapped[str] = mapped_column(String(64))
    parking_slot: Mapped[str | None] = mapped_column(String(32), default=None)
    firmware_version: Mapped[str | None] = mapped_column(String(32), default=None)
    frame_version: Mapped[int | None] = mapped_column(default=None)
    is_active: Mapped[bool] = mapped_column(default=True)
    registered_at: Mapped[datetime] = mapped_column(UtcDateTime)

    # 의도적 비정규화 (docs/db-schema.md D7) — 헬스체크·유실 판정 비용 절감
    last_seen_at: Mapped[datetime | None] = mapped_column(UtcDateTime, default=None)
    last_seq: Mapped[int | None] = mapped_column(default=None)
    last_state: Mapped[str | None] = mapped_column(String(8), default=None)


class ReadingOrm(Base):
    """수신 프레임 전량. state는 노드가 보낸 원본 값이다 (D2)."""

    __tablename__ = "readings"
    __table_args__ = (
        # LoRa 재전송 멱등. seq 랩어라운드 대비 measured_at 포함
        UniqueConstraint("device_id", "measured_at", "seq", name="uq_readings_frame"),
        Index("ix_readings_device_time", "device_id", "measured_at"),
        CheckConstraint(
            "state IN ('WARMUP','NORMAL','WATCH','ALARM','FAULT')",
            name="ck_readings_state",
        ),
        CheckConstraint("temp_c IS NULL OR (temp_c BETWEEN -40 AND 125)", name="ck_readings_temp"),
        CheckConstraint(
            "humidity_pct IS NULL OR (humidity_pct BETWEEN 0 AND 100)",
            name="ck_readings_humidity",
        ),
        CheckConstraint("rssi IS NULL OR rssi <= 0", name="ck_readings_rssi"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"))
    seq: Mapped[int]
    measured_at: Mapped[datetime] = mapped_column(UtcDateTime)
    received_at: Mapped[datetime] = mapped_column(UtcDateTime)
    frame_version: Mapped[int]
    state: Mapped[str] = mapped_column(String(8))

    # 가스 채널: 정규화 + 변화율만. raw 미저장 (D3)
    voc_dev: Mapped[float | None] = mapped_column(default=None)
    voc_slope: Mapped[float | None] = mapped_column(default=None)
    h2_dev: Mapped[float | None] = mapped_column(default=None)
    h2_slope: Mapped[float | None] = mapped_column(default=None)
    co_dev: Mapped[float | None] = mapped_column(default=None)
    co_slope: Mapped[float | None] = mapped_column(default=None)

    # 환경·구조 채널
    temp_c: Mapped[float | None] = mapped_column(default=None)
    humidity_pct: Mapped[float | None] = mapped_column(default=None)
    pressure_hpa: Mapped[float | None] = mapped_column(default=None)
    water_level_mm: Mapped[float | None] = mapped_column(default=None)

    # 통신 품질 — 유실 원인 추적의 유일한 지표
    rssi: Mapped[int | None] = mapped_column(default=None)
    snr: Mapped[float | None] = mapped_column(default=None)


class AlertOrm(Base):
    """상태 전이 이벤트. readings의 요약이지 그 반대가 아니다."""

    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_device_time", "device_id", "occurred_at"),
        # 부분 인덱스 — 활성 알람 조회를 이력 크기와 무관하게 유지
        Index(
            "ix_alerts_active",
            "device_id",
            sqlite_where=text("acknowledged_at IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"))
    reading_id: Mapped[int | None] = mapped_column(ForeignKey("readings.id"), default=None)
    from_state: Mapped[str] = mapped_column(String(8))
    to_state: Mapped[str] = mapped_column(String(8))
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime)
    detected_at: Mapped[datetime] = mapped_column(UtcDateTime)
    acknowledged_at: Mapped[datetime | None] = mapped_column(UtcDateTime, default=None)
    acknowledged_note: Mapped[str | None] = mapped_column(String(255), default=None)


class DeviceTokenOrm(Base):
    """앱 푸시 토큰. 재등록이 중복 행을 만들지 않게 unique."""

    __tablename__ = "device_tokens"
    __table_args__ = (CheckConstraint("platform IN ('android','ios')", name="ck_tokens_platform"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(255), unique=True)
    platform: Mapped[str] = mapped_column(String(8))
    registered_at: Mapped[datetime] = mapped_column(UtcDateTime)
    last_used_at: Mapped[datetime | None] = mapped_column(UtcDateTime, default=None)
    is_active: Mapped[bool] = mapped_column(default=True)
    deactivated_reason: Mapped[str | None] = mapped_column(String(64), default=None)


class PushDeliveryOrm(Base):
    """발송 시도 이력. 실패 원인 추적 근거."""

    __tablename__ = "push_deliveries"
    __table_args__ = (
        Index("ix_push_deliveries_alert", "alert_id"),
        CheckConstraint(
            "status IN ('pending','sent','failed_retryable','failed_permanent')",
            name="ck_deliveries_status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id"))
    token_id: Mapped[int] = mapped_column(ForeignKey("device_tokens.id"))
    attempt: Mapped[int]
    status: Mapped[str] = mapped_column(String(20))
    error_code: Mapped[str | None] = mapped_column(String(64), default=None)
    sent_at: Mapped[datetime | None] = mapped_column(UtcDateTime, default=None)
