"""규칙이 위반을 실제로 잡는지 확인한다.

전체 통과는 규칙이 작동한다는 증거가 아니다 — 오타 난 규칙도 항상 통과한다.
위반 소스를 문자열로 넣어 발화를 직접 본다.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

import pytest

from tests.architecture import rules
from tests.architecture.engine import Rule, Violation

_ELSEWHERE = Path("somewhere/else.py")

_CASES: list[tuple[Rule, str]] = [
    # tz를 붙여도 금지다 — ruff DTZ가 통과시키는 케이스를 이 규칙이 잡아야 한다.
    (rules.forbid_direct_clock, "from datetime import UTC, datetime\nx = datetime.now(UTC)\n"),
    (rules.forbid_direct_env, "import os\nx = os.getenv('APP_DATABASE_PATH')\n"),
    (rules.forbid_manual_transaction, "def save(session):\n    session.commit()\n"),
    (rules.forbid_legacy_query_api, "def find(session):\n    return session.query(Row).all()\n"),
    (rules.forbid_pydantic_v1_api, "def load(raw):\n    return Model.parse_obj(raw)\n"),
    (
        rules.forbid_handwritten_init,
        "class Sender:\n    def __init__(self, client):\n        self._client = client\n",
    ),
    (rules.forbid_domain_status_code, "class Boom(Exception):\n    status_code: int = 404\n"),
]


@pytest.mark.parametrize(
    ("rule", "source"), _CASES, ids=lambda value: getattr(value, "__name__", "")
)
def test_rule_fires_on_violation(rule: Rule, source: str) -> None:
    assert _run(rule, source), "규칙이 위반 소스를 잡지 못한다"


_CLEAN_CASES: list[tuple[Rule, str]] = [
    # Clock port 주입은 정상이다.
    (rules.forbid_direct_clock, "def run(clock):\n    return clock.now()\n"),
    # 파생 계산이 있으면 dataclass 대체 대상이 아니다.
    (
        rules.forbid_handwritten_init,
        "class Sender:\n    def __init__(self, client):\n        self._owns = client is None\n",
    ),
    # dataclass는 애초에 대상이 아니다.
    (
        rules.forbid_handwritten_init,
        "@dataclass(frozen=True)\nclass Repo:\n    def __init__(self, s):\n        self.s = s\n",
    ),
]


@pytest.mark.parametrize(
    ("rule", "source"), _CLEAN_CASES, ids=lambda value: getattr(value, "__name__", "")
)
def test_rule_stays_quiet_on_valid_code(rule: Rule, source: str) -> None:
    assert not _run(rule, source), "규칙이 정상 코드를 위반으로 신고한다"


def _run(rule: Rule, source: str) -> list[Violation]:
    result: Iterator[Violation] = rule(ast.parse(source), _ELSEWHERE)
    return list(result)
