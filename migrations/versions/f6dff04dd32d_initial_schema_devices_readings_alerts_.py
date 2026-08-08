"""initial schema: devices readings alerts push

Revision ID: f6dff04dd32d
Revises:
Create Date: 2026-08-08

autogenerate 초안을 검토·수정했다:
- 커스텀 타입을 `app.infrastructure.db.types.UtcDateTime`으로 뱉었으나 import가
  없어 실행 시 NameError. import 추가 후 짧은 이름으로 교체.
- typing.Union/Sequence 구식 표기를 모던 표기로.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.infrastructure.db.types import UtcDateTime

revision: str = "f6dff04dd32d"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hw_id", sa.String(length=32), nullable=False),
        sa.Column("label", sa.String(length=64), nullable=False),
        sa.Column("parking_slot", sa.String(length=32), nullable=True),
        sa.Column("firmware_version", sa.String(length=32), nullable=True),
        sa.Column("frame_version", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("registered_at", UtcDateTime(length=32), nullable=False),
        # 의도적 비정규화 (docs/db-schema.md D7)
        sa.Column("last_seen_at", UtcDateTime(length=32), nullable=True),
        sa.Column("last_seq", sa.Integer(), nullable=True),
        sa.Column("last_state", sa.String(length=8), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("hw_id"),
    )

    op.create_table(
        "readings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("measured_at", UtcDateTime(length=32), nullable=False),
        sa.Column("received_at", UtcDateTime(length=32), nullable=False),
        sa.Column("frame_version", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=8), nullable=False),
        # 가스 채널: 정규화 + 변화율. raw 미저장 (D3)
        sa.Column("voc_dev", sa.Float(), nullable=True),
        sa.Column("voc_slope", sa.Float(), nullable=True),
        sa.Column("h2_dev", sa.Float(), nullable=True),
        sa.Column("h2_slope", sa.Float(), nullable=True),
        sa.Column("co_dev", sa.Float(), nullable=True),
        sa.Column("co_slope", sa.Float(), nullable=True),
        sa.Column("temp_c", sa.Float(), nullable=True),
        sa.Column("humidity_pct", sa.Float(), nullable=True),
        sa.Column("pressure_hpa", sa.Float(), nullable=True),
        sa.Column("water_level_mm", sa.Float(), nullable=True),
        sa.Column("rssi", sa.Integer(), nullable=True),
        sa.Column("snr", sa.Float(), nullable=True),
        sa.CheckConstraint(
            "state IN ('WARMUP','NORMAL','WATCH','ALARM','FAULT')",
            name="ck_readings_state",
        ),
        sa.CheckConstraint(
            "humidity_pct IS NULL OR (humidity_pct BETWEEN 0 AND 100)",
            name="ck_readings_humidity",
        ),
        sa.CheckConstraint("rssi IS NULL OR rssi <= 0", name="ck_readings_rssi"),
        sa.CheckConstraint(
            "temp_c IS NULL OR (temp_c BETWEEN -40 AND 125)", name="ck_readings_temp"
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.PrimaryKeyConstraint("id"),
        # LoRa 재전송 멱등
        sa.UniqueConstraint("device_id", "measured_at", "seq", name="uq_readings_frame"),
    )
    op.create_index(
        "ix_readings_device_time", "readings", ["device_id", "measured_at"], unique=False
    )

    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("reading_id", sa.Integer(), nullable=True),
        sa.Column("from_state", sa.String(length=8), nullable=False),
        sa.Column("to_state", sa.String(length=8), nullable=False),
        sa.Column("occurred_at", UtcDateTime(length=32), nullable=False),
        sa.Column("detected_at", UtcDateTime(length=32), nullable=False),
        sa.Column("acknowledged_at", UtcDateTime(length=32), nullable=True),
        sa.Column("acknowledged_note", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.ForeignKeyConstraint(["reading_id"], ["readings.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alerts_device_time", "alerts", ["device_id", "occurred_at"], unique=False)
    # 부분 인덱스 — 활성 알람 조회를 이력 크기와 무관하게 유지
    op.create_index(
        "ix_alerts_active",
        "alerts",
        ["device_id"],
        unique=False,
        sqlite_where=sa.text("acknowledged_at IS NULL"),
    )

    op.create_table(
        "device_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=8), nullable=False),
        sa.Column("registered_at", UtcDateTime(length=32), nullable=False),
        sa.Column("last_used_at", UtcDateTime(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deactivated_reason", sa.String(length=64), nullable=True),
        sa.CheckConstraint("platform IN ('android','ios')", name="ck_tokens_platform"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )

    op.create_table(
        "push_deliveries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=False),
        sa.Column("token_id", sa.Integer(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("sent_at", UtcDateTime(length=32), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','sent','failed_retryable','failed_permanent')",
            name="ck_deliveries_status",
        ),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"]),
        sa.ForeignKeyConstraint(["token_id"], ["device_tokens.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_push_deliveries_alert", "push_deliveries", ["alert_id"], unique=False)


def downgrade() -> None:
    # 운영 롤백 수단으로 신뢰하지 않는다 — 롤백 정본은 DB 백업 복원.
    op.drop_index("ix_push_deliveries_alert", table_name="push_deliveries")
    op.drop_table("push_deliveries")
    op.drop_table("device_tokens")
    op.drop_index("ix_alerts_active", table_name="alerts")
    op.drop_index("ix_alerts_device_time", table_name="alerts")
    op.drop_table("alerts")
    op.drop_index("ix_readings_device_time", table_name="readings")
    op.drop_table("readings")
    op.drop_table("devices")
