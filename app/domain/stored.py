"""저장된 뒤에만 존재하는 식별자.

저장 전과 후를 한 타입으로 표현하므로 호출부가 `id or 0`으로 뭉갤 수 있다 —
존재하지 않는 FK 0이 조용히 흘러가는 경로다. 없으면 즉시 실패시켜 그 경로를 막는다.
"""

from __future__ import annotations


class NotStored(RuntimeError):
    """저장되지 않은 객체의 식별자를 요구했다.

    업무 규칙 위반이 아니라 호출 순서 결함이다 — 도메인 예외가 아니므로 500으로 뜬다.
    """


def require_stored(identifier: int | None, name: str) -> int:
    if identifier is None:
        raise NotStored(f"{name}가 아직 저장되지 않았다 — 식별자가 없다")
    return identifier
