"""수신 생존 상태 단위 테스트.

헬스체크가 "무선 두절"을 판단하는 유일한 근거다 — 여기가 틀리면 수신이 멈춘 걸
아무도 모른다.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from app.runtime.state import ReceiverLiveness

_NOW = datetime(2026, 8, 8, 12, 0, tzinfo=UTC)


class TestSilence:
    def test_never_received_has_no_silence_measure(self) -> None:
        """한 번도 못 받은 것과 '방금 받았다'를 0초로 뭉개지 않는다."""
        assert ReceiverLiveness(label="lora", enabled=True).silence_s(_NOW) is None

    def test_silence_is_measured_from_last_frame(self) -> None:
        liveness = ReceiverLiveness(label="lora", enabled=True)
        liveness.observe(_NOW - timedelta(seconds=42))

        assert liveness.silence_s(_NOW) == 42.0


class TestStop:
    async def test_cancels_and_reaps_the_task(self) -> None:
        """회수하지 않으면 종료가 매달린다."""
        started = asyncio.Event()

        async def forever() -> None:
            started.set()
            await asyncio.Event().wait()

        liveness = ReceiverLiveness(label="lora", enabled=True, task=asyncio.create_task(forever()))
        await started.wait()

        await liveness.stop()

        assert liveness.enabled is False
        assert liveness.task is None

    async def test_stopping_without_a_task_is_allowed(self) -> None:
        """lora_enabled=false로 뜬 프로세스도 같은 종료 경로를 탄다."""
        liveness = ReceiverLiveness(label="lora", enabled=False)

        await liveness.stop()

        assert liveness.enabled is False
