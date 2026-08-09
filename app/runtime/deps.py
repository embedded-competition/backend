"""요청 스코프 자원 — 설정·세션. 서비스 조립은 providers.py, 인증은 auth.py."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings


def settings_dep() -> Settings:
    return get_settings()


def session_factory_dep(request: Request) -> sessionmaker[Session]:
    factory = getattr(request.app.state, "session_factory", None)
    if factory is None:  # pragma: no cover - lifespan이 항상 채운다
        raise RuntimeError("session_factory가 lifespan에서 초기화되지 않았다")
    return factory  # type: ignore[no-any-return]


def session_dep(
    factory: Annotated[sessionmaker[Session], Depends(session_factory_dep)],
) -> Iterator[Session]:
    """요청 1개 = 트랜잭션 1개. commit/rollback 경계가 여기다."""
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


SettingsDep = Annotated[Settings, Depends(settings_dep)]
SessionDep = Annotated[Session, Depends(session_dep)]
