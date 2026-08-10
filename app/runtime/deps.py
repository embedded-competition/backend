from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.runtime.state import STATE_ATTRIBUTE, RuntimeState


def settings_dep() -> Settings:
    return get_settings()


def runtime_state_dep(request: Request) -> RuntimeState:
    state = getattr(request.app.state, STATE_ATTRIBUTE, None)
    if not isinstance(state, RuntimeState):
        raise RuntimeError("lifespan이 RuntimeState를 올리지 않았다")
    return state


def session_dep(state: Annotated[RuntimeState, Depends(runtime_state_dep)]) -> Iterator[Session]:
    session = state.session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


SettingsDep = Annotated[Settings, Depends(settings_dep)]
RuntimeStateDep = Annotated[RuntimeState, Depends(runtime_state_dep)]
SessionDep = Annotated[Session, Depends(session_dep)]
