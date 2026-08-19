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

from app.domain.value_objects import Condition
from app.infrastructure.db.types import ConditionSet, UtcDateTime


class Base(DeclarativeBase):
    pass


class DeviceOrm(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    public_id: Mapped[str] = mapped_column(String(32), unique=True)
    mac: Mapped[str] = mapped_column(String(17), unique=True)
    hw_id: Mapped[str | None] = mapped_column(String(32), unique=True, default=None)
    label: Mapped[str] = mapped_column(String(64))
    parking_slot: Mapped[str | None] = mapped_column(String(32), default=None)
    management_phone: Mapped[str | None] = mapped_column(String(32), default=None)
    firmware_version: Mapped[str | None] = mapped_column(String(32), default=None)
    frame_version: Mapped[int | None] = mapped_column(default=None)
    is_active: Mapped[bool] = mapped_column(default=True)
    registered_at: Mapped[datetime] = mapped_column(UtcDateTime)

    last_seen_at: Mapped[datetime | None] = mapped_column(UtcDateTime, default=None)
    last_seq: Mapped[int | None] = mapped_column(default=None)
    last_state: Mapped[str | None] = mapped_column(String(8), default=None)


class ReadingOrm(Base):
    __tablename__ = "readings"
    __table_args__ = (
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
    conditions: Mapped[frozenset[Condition] | None] = mapped_column(ConditionSet, default=None)
    latched: Mapped[bool | None] = mapped_column(default=None)

    voc_dev: Mapped[float | None] = mapped_column(default=None)
    voc_slope: Mapped[float | None] = mapped_column(default=None)
    h2_dev: Mapped[float | None] = mapped_column(default=None)
    h2_slope: Mapped[float | None] = mapped_column(default=None)
    co_dev: Mapped[float | None] = mapped_column(default=None)
    co_slope: Mapped[float | None] = mapped_column(default=None)

    sig_rise: Mapped[bool | None] = mapped_column(default=None)
    sig_hold: Mapped[bool | None] = mapped_column(default=None)
    sig_no_recover: Mapped[bool | None] = mapped_column(default=None)
    sig_hold_s: Mapped[int | None] = mapped_column(default=None)

    temp_c: Mapped[float | None] = mapped_column(default=None)
    humidity_pct: Mapped[float | None] = mapped_column(default=None)
    d_rh_dt: Mapped[float | None] = mapped_column(default=None)
    pressure_dev: Mapped[float | None] = mapped_column(default=None)
    pressure_rate: Mapped[float | None] = mapped_column(default=None)
    water_level: Mapped[float | None] = mapped_column(default=None)
    water: Mapped[bool | None] = mapped_column(default=None)

    batt_mv: Mapped[int | None] = mapped_column(default=None)
    lat: Mapped[float | None] = mapped_column(default=None)
    lon: Mapped[float | None] = mapped_column(default=None)

    rssi: Mapped[int | None] = mapped_column(default=None)
    snr: Mapped[float | None] = mapped_column(default=None)


class AlertOrm(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_device_time", "device_id", "occurred_at"),
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


class AccessTokenOrm(Base):
    __tablename__ = "access_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(UtcDateTime)
    last_used_at: Mapped[datetime | None] = mapped_column(UtcDateTime, default=None)


class PushTokenOrm(Base):
    __tablename__ = "push_tokens"
    __table_args__ = (
        CheckConstraint(
            "platform IS NULL OR platform IN ('android','ios')",
            name="ck_push_tokens_platform",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"))
    token: Mapped[str] = mapped_column(String(255), unique=True)
    platform: Mapped[str | None] = mapped_column(String(8), default=None)
    registered_at: Mapped[datetime] = mapped_column(UtcDateTime)
    last_used_at: Mapped[datetime | None] = mapped_column(UtcDateTime, default=None)
    is_active: Mapped[bool] = mapped_column(default=True)
    deactivated_reason: Mapped[str | None] = mapped_column(String(64), default=None)


class PushDeliveryOrm(Base):
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
    token_id: Mapped[int] = mapped_column(ForeignKey("push_tokens.id"))
    attempt: Mapped[int]
    status: Mapped[str] = mapped_column(String(20))
    error_code: Mapped[str | None] = mapped_column(String(64), default=None)
    sent_at: Mapped[datetime | None] = mapped_column(UtcDateTime, default=None)


class EventOrm(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_device_time", "device_id", "occurred_at"),
        CheckConstraint("kind IN ('state_change','action','suppressed')", name="ck_events_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"))
    alert_id: Mapped[int | None] = mapped_column(ForeignKey("alerts.id"), default=None)
    kind: Mapped[str] = mapped_column(String(16))
    occurred_at: Mapped[datetime] = mapped_column(UtcDateTime)
    description: Mapped[str] = mapped_column(String(255))
