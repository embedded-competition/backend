"""add reading water_level column

Revision ID: 90a4921eed4b
Revises: f36a78b22510
Create Date: 2026-08-13

노드가 수위를 0~1000 정규화 레벨로 보낸다. 기존 `water` bool은 "잠겼는가"라는
판정이고, 이 컬럼은 그 판정의 근거가 되는 값이다 — 둘은 다른 질문이라 같은
자리에 담기지 않는다.

Expand — 컬럼만 추가한다. 기존 행은 NULL로 남고, 그 시절 프레임에 수위 값이
없었다는 사실을 그대로 뜻한다. 0으로 채우면 "물이 없었다"는 없는 판독을
지어내는 것이라 백필하지 않는다.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "90a4921eed4b"
down_revision: str | None = "f36a78b22510"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("readings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("water_level", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("readings", schema=None) as batch_op:
        batch_op.drop_column("water_level")
