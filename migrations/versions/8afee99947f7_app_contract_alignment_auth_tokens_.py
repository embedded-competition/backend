"""app contract alignment: auth tokens, events, signature, gps

Revision ID: 8afee99947f7
Revises: f6dff04dd32d
Create Date: 2026-08-08

앱 repo(embedded-competition/app)의 api-spec.md·interface.md와 정합화한 결과.
근거와 미해결 항목은 docs/api-contract-reconciliation.md.

autogenerate 초안을 검토·수정했다:
- UtcDateTime을 FQN으로 뱉고 import를 안 넣어 실행 시 NameError (초기 리비전과 동일 사고)
- 익명 제약(create_unique_constraint(None, ...))에 이름 부여 — 이름 없으면 downgrade가
  어떤 제약을 지우는지 특정하지 못한다
- typing.Union/Sequence 구식 표기 정리

**파괴적 변경 주의**: devices.public_id·mac을 NOT NULL로 추가하고 readings에서
pressure_hpa·water_level_mm을 삭제한다. batch 모드가 테이블을 재생성하므로 기존 행이
있으면 NOT NULL 위반으로 실패한다. 이 리비전은 아직 어디에도 배포되지 않은 스키마를
전제로 한다 — 이미 데이터가 있는 DB에 적용해야 한다면 백필 단계를 먼저 넣어야 한다.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.infrastructure.db.types import UtcDateTime

revision: str = "8afee99947f7"
down_revision: str | None = "f6dff04dd32d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # deviceToken 해시 (D9). 원문 저장 안 함
    op.create_table(
        "access_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", UtcDateTime(length=32), nullable=False),
        sa.Column("last_used_at", UtcDateTime(length=32), nullable=True),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_access_tokens_hash"),
    )

    # Expo 푸시 토큰 (구 device_tokens)
    op.create_table(
        "push_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("platform", sa.String(length=8), nullable=True),
        sa.Column("registered_at", UtcDateTime(length=32), nullable=False),
        sa.Column("last_used_at", UtcDateTime(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("deactivated_reason", sa.String(length=64), nullable=True),
        sa.CheckConstraint(
            "platform IS NULL OR platform IN ('android','ios')",
            name="ck_push_tokens_platform",
        ),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token", name="uq_push_tokens_token"),
    )

    # 기록 탭 서술 로그 (D10)
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("alert_id", sa.Integer(), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("occurred_at", UtcDateTime(length=32), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.CheckConstraint("kind IN ('state_change','action','suppressed')", name="ck_events_kind"),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"]),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_events_device_time", "events", ["device_id", "occurred_at"])

    # push_deliveries는 device_tokens를 FK로 참조한다. 참조를 먼저 끊지 않고 테이블을
    # 지우면 이후 batch 재생성이 반영에 실패한다.
    # SQLite 인라인 FK는 이름이 없어 batch drop_constraint로 특정할 수 없으므로,
    # 빈 테이블을 통째로 재생성한다 (배포 전이라 데이터 없음).
    op.drop_table("push_deliveries")
    op.drop_table("device_tokens")
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
        sa.ForeignKeyConstraint(["token_id"], ["push_tokens.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_push_deliveries_alert", "push_deliveries", ["alert_id"])

    with op.batch_alter_table("devices", schema=None) as batch_op:
        batch_op.add_column(sa.Column("public_id", sa.String(length=32), nullable=False))
        batch_op.add_column(sa.Column("mac", sa.String(length=17), nullable=False))
        batch_op.add_column(sa.Column("management_phone", sa.String(length=32), nullable=True))
        # 앱이 MAC으로 먼저 등록하고, 노드가 첫 프레임을 보낼 때 hw_id가 채워진다
        batch_op.alter_column("hw_id", existing_type=sa.VARCHAR(length=32), nullable=True)
        batch_op.create_unique_constraint("uq_devices_mac", ["mac"])
        batch_op.create_unique_constraint("uq_devices_public_id", ["public_id"])

    with op.batch_alter_table("readings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("latched", sa.Boolean(), nullable=True))
        # signature 3요소 — 노드가 계산해 전송 (정합화 B1)
        batch_op.add_column(sa.Column("sig_rise", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("sig_hold", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("sig_no_recover", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("sig_hold_s", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("d_rh_dt", sa.Float(), nullable=True))
        # pressure_hpa(절대 단위) → pressure_dev/rate(정규화). 앱 presDev/presRate 대응
        batch_op.add_column(sa.Column("pressure_dev", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("pressure_rate", sa.Float(), nullable=True))
        # water_level_mm(mm) → water(bool). 확증 보너스라 유무만 필요
        batch_op.add_column(sa.Column("water", sa.Boolean(), nullable=True))
        batch_op.add_column(sa.Column("batt_mv", sa.Integer(), nullable=True))
        # GPS 미장착이면 NULL (정합화 C2)
        batch_op.add_column(sa.Column("lat", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("lon", sa.Float(), nullable=True))
        batch_op.drop_column("water_level_mm")
        batch_op.drop_column("pressure_hpa")


def downgrade() -> None:
    # 운영 롤백 수단으로 신뢰하지 않는다 — 롤백 정본은 DB 백업 복원.
    with op.batch_alter_table("readings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("pressure_hpa", sa.FLOAT(), nullable=True))
        batch_op.add_column(sa.Column("water_level_mm", sa.FLOAT(), nullable=True))
        for column in (
            "lon",
            "lat",
            "batt_mv",
            "water",
            "pressure_rate",
            "pressure_dev",
            "d_rh_dt",
            "sig_hold_s",
            "sig_no_recover",
            "sig_hold",
            "sig_rise",
            "latched",
        ):
            batch_op.drop_column(column)

    with op.batch_alter_table("devices", schema=None) as batch_op:
        batch_op.drop_constraint("uq_devices_public_id", type_="unique")
        batch_op.drop_constraint("uq_devices_mac", type_="unique")
        batch_op.alter_column("hw_id", existing_type=sa.VARCHAR(length=32), nullable=False)
        batch_op.drop_column("management_phone")
        batch_op.drop_column("mac")
        batch_op.drop_column("public_id")

    # upgrade와 대칭: push_deliveries를 지우고 device_tokens 복원 후 재생성
    op.drop_index("ix_push_deliveries_alert", table_name="push_deliveries")
    op.drop_table("push_deliveries")
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
    op.create_index("ix_push_deliveries_alert", "push_deliveries", ["alert_id"])
    op.drop_index("ix_events_device_time", table_name="events")
    op.drop_table("events")
    op.drop_table("push_tokens")
    op.drop_table("access_tokens")
