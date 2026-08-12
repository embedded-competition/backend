"""add reading conditions column

Revision ID: f36a78b22510
Revises: 8afee99947f7
Create Date: 2026-08-12

state 하나로 접혀 있던 "무슨 일이 일어나는가"를 conditions로 분리해 살린다
(app/domain/value_objects/condition.py). Expand — 컬럼만 추가한다. 기존 행은
NULL로 남고, 저장소가 읽을 때 빈 조건으로 취급한다 (조회 시점 백필, 별도
백필 단계 불필요 — 과거 프레임의 원인은 재구성할 수 없다).

autogenerate 초안을 검토·수정했다: ConditionSet을 FQN으로 뱉고 import를 안
넣어 실행 시 NameError (8afee99947f7과 동일 사고).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.infrastructure.db.types import ConditionSet

revision: str = "f36a78b22510"
down_revision: str | None = "8afee99947f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("readings", schema=None) as batch_op:
        batch_op.add_column(sa.Column("conditions", ConditionSet(length=64), nullable=True))


def downgrade() -> None:
    # 운영 롤백 수단으로 신뢰하지 않는다 — 롤백 정본은 DB 백업 복원.
    with op.batch_alter_table("readings", schema=None) as batch_op:
        batch_op.drop_column("conditions")
