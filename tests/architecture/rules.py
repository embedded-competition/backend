"""금지형 규칙 정의. 실행은 test_*.py, 발화 검증은 test_rules_fire.py."""

from __future__ import annotations

import ast
from collections.abc import Iterator
from pathlib import Path

from tests.architecture import lint_target as target
from tests.architecture.engine import Violation, calls, dotted_name, is_dataclass

_CLOCK_CALLS = frozenset(
    {"datetime.now", "datetime.utcnow", "date.today", "time.time", "time.monotonic"}
)
_ENV_CALLS = frozenset({"os.getenv", "os.environ.get", "getenv"})


def forbid_direct_clock(tree: ast.AST, path: Path) -> Iterator[Violation]:
    """시각은 Clock port로만 들어온다 (domain.md).

    ruff DTZ는 tz 인자 누락만 잡는다. domain·core에서는 tz가 붙어 있어도 금지다
    — 테스트가 시각을 고정할 수 없게 되기 때문이다.
    """
    if path == target.CLOCK_ADAPTER:
        return
    for node, name in calls(tree):
        if name in _CLOCK_CALLS:
            yield Violation(path, node.lineno, f"{name}() 직접 호출 — Clock port를 주입한다")


def forbid_direct_env(tree: ast.AST, path: Path) -> Iterator[Violation]:
    """설정 SSOT는 Settings다. 흩어진 getenv는 오타가 조용히 기본값으로 흐른다."""
    if path == target.CONFIG_MODULE:
        return
    for node, name in calls(tree):
        if name in _ENV_CALLS:
            yield Violation(path, node.lineno, f"{name} — 설정은 core.config.Settings가 소유한다")


def forbid_manual_transaction(tree: ast.AST, path: Path) -> Iterator[Violation]:
    """트랜잭션 경계는 세션 스코프 하나뿐이다 (service.md).

    저장소나 서비스가 커밋하면 유스케이스 하나가 여러 트랜잭션으로 쪼개진다.
    """
    if path in target.TRANSACTION_SCOPES:
        return
    for node, name in calls(tree):
        if name.endswith((".commit", ".rollback")):
            yield Violation(path, node.lineno, f"{name}() — 트랜잭션 경계는 세션 스코프가 소유")


def forbid_legacy_query_api(tree: ast.AST, path: Path) -> Iterator[Violation]:
    """SQLAlchemy 1.x `session.query()` 금지 — 2.0 `select()`를 쓴다."""
    for node, name in calls(tree):
        if name.endswith("session.query"):
            yield Violation(path, node.lineno, "session.query() — 2.0 select() 스타일을 쓴다")


def forbid_business_method_on_orm(tree: ast.AST, path: Path) -> Iterator[Violation]:
    """ORM 클래스는 매핑 전용. 행위는 domain dataclass가 갖는다 (repository.md)."""
    if path != target.ORM_MODULE:
        return
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for member in node.body:
            if isinstance(member, ast.FunctionDef) and not member.name.startswith("_"):
                yield Violation(
                    path, member.lineno, f"{node.name}.{member.name}() — ORM에 비즈니스 로직"
                )


def forbid_handwritten_init(tree: ast.AST, path: Path) -> Iterator[Violation]:
    """`__init__`이 파라미터 보관만 하면 dataclass가 그 코드를 대신 쓴다.

    파생 계산·검증·부수효과가 하나라도 있으면 대상이 아니다 — 그건 dataclass로
    옮기면 `__post_init__`으로 흩어져 오히려 읽기 어려워진다.
    """
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or is_dataclass(node):
            continue
        init = next(
            (m for m in node.body if isinstance(m, ast.FunctionDef) and m.name == "__init__"),
            None,
        )
        if init is None or not init.body:
            continue
        if all(_is_storage_assignment(stmt) for stmt in init.body):
            yield Violation(
                path, init.lineno, f"{node.name}.__init__이 보관뿐 — @dataclass로 대체 가능"
            )


def _is_storage_assignment(stmt: ast.stmt) -> bool:
    """`self.x = param` 또는 `self.x = Default()` 형태인가."""
    if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
        return False
    target_node = stmt.targets[0]
    if not (
        isinstance(target_node, ast.Attribute)
        and isinstance(target_node.value, ast.Name)
        and target_node.value.id == "self"
    ):
        return False
    value = stmt.value
    if isinstance(value, ast.Name):
        return True
    return isinstance(value, ast.Call) and not value.args and not value.keywords


def forbid_pydantic_v1_api(tree: ast.AST, path: Path) -> Iterator[Violation]:
    """v1 메서드는 v2에서 조용히 다르게 동작한다 (schema.md)."""
    for node, name in calls(tree):
        attribute = name.rsplit(".", 1)[-1]
        if attribute in {"parse_obj", "parse_raw", "from_orm"}:
            yield Violation(path, node.lineno, f"{name}() — pydantic v1 API. model_* 를 쓴다")


def forbid_domain_status_code(tree: ast.AST, path: Path) -> Iterator[Violation]:
    """도메인 예외는 HTTP를 모른다. 매핑은 api/errors.py 한 곳이다 (domain.md)."""
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and dotted_name(node.target) == "status_code":
            yield Violation(path, node.lineno, "status_code 필드 — HTTP 매핑은 api 계층")
        if isinstance(node, ast.Assign) and any(
            dotted_name(t) == "status_code" for t in node.targets
        ):
            yield Violation(path, node.lineno, "status_code 필드 — HTTP 매핑은 api 계층")
