"""SQLite 엔진·세션. PRAGMA는 커넥션마다 적용돼야 한다."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker


def _apply_pragmas(dbapi_connection: Any, _record: Any) -> None:
    """커넥션 생성마다 실행. 앱 시작 시 1회만 걸면 새 커넥션에 안 붙는다."""
    if not isinstance(dbapi_connection, sqlite3.Connection):
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")  # 쓰기 중 읽기 허용
        cursor.execute("PRAGMA synchronous=NORMAL")  # SD카드 write 감소
        cursor.execute("PRAGMA foreign_keys=ON")  # 미설정 시 FK가 조용히 무시됨
        cursor.execute("PRAGMA busy_timeout=5000")  # 쓰기 락 대기
    finally:
        cursor.close()


def create_db_engine(
    database_path: Path, *, busy_timeout_ms: int = 5_000, pool_size: int = 5
) -> Engine:
    """설정 객체가 아니라 필요한 값만 받는다 — infrastructure는 core를 모른다."""
    database_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite+pysqlite:///{database_path}",
        # 워커 1개 + 수신 task 1개 구조. 큰 풀은 512MB에서 낭비다.
        pool_size=pool_size,
        max_overflow=0,
        connect_args={"timeout": busy_timeout_ms / 1000},
    )
    event.listen(engine, "connect", _apply_pragmas)
    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    # 커밋 후 ORM 객체를 계속 쓰지 않는다 — repository가 domain 객체로 변환해 반환.
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """트랜잭션 경계 1개. 백그라운드 수신 task가 프레임 단위로 사용한다."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
