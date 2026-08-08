"""Alembic 환경.

DB URL은 app.core.config의 Settings에서 온다 — alembic.ini에 하드코딩하지 않는다.
render_as_batch=True: SQLite는 ALTER TABLE이 제한적이라 컬럼 삭제·타입 변경·
제약 추가가 직접 안 된다. autogenerate가 batch 블록을 만들게 한다.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.core.config import get_settings
from app.infrastructure.db.orm import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 호출자가 URL을 주입했으면 그걸 쓴다 (테스트가 임시 DB를 가리키게 하는 경로).
# 주입이 없을 때만 Settings에서 채운다.
if not config.get_main_option("sqlalchemy.url", None):
    config.set_main_option("sqlalchemy.url", get_settings().database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
