"""lifespan이 소유하는 프로세스 자원.

FastAPI의 `app.state`는 무엇이 들었는지 열어 봐야 아는 자료 뭉치다. 이름 있는 타입
하나만 올려서, 읽는 쪽이 getattr 기본값으로 없는 필드를 추측하지 않게 한다.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session, sessionmaker

# app.state에 올릴 때 쓰는 유일한 키. 문자열이 흩어지면 오타가 조용히 None이 된다.
STATE_ATTRIBUTE = "runtime"


@dataclass(slots=True)
class ReceiverLiveness:
    """수신 task 생존 근거. 헬스체크가 읽는 유일한 출처다."""

    enabled: bool

    last_frame_at: datetime | None = None
    task: asyncio.Task[None] | None = None
    """지역 변수로만 두면 GC가 실행 중인 task를 거둬 간다."""

    def observe(self, at: datetime) -> None:
        self.last_frame_at = at

    def silence_s(self, now: datetime) -> float | None:
        """마지막 수신 이후 흐른 시간. 한 번도 못 받았으면 None."""
        if self.last_frame_at is None:
            return None
        return (now - self.last_frame_at).total_seconds()

    async def stop(self) -> None:
        self.enabled = False
        if self.task is None:
            return
        self.task.cancel()
        # 취소된 task를 회수하지 않으면 종료가 매달린다.
        await asyncio.gather(self.task, return_exceptions=True)
        self.task = None


@dataclass(slots=True)
class RuntimeState:
    """프로세스 수명과 함께 사는 것들. 요청 스코프 자원은 여기 두지 않는다."""

    session_factory: sessionmaker[Session]
    schema_revision: str | None = None
    lora: ReceiverLiveness = field(default_factory=lambda: ReceiverLiveness(enabled=False))
