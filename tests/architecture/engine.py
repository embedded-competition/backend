"""AST 규칙 실행기.

규칙은 `(tree, path) -> Iterator[Violation]` 함수다. 테스트가 아니라 순수 함수라
문자열 소스에 직접 돌릴 수 있고, 그래서 "규칙이 실제로 발화하는가"를 별도로
검증할 수 있다 (test_rules_fire.py).
"""

from __future__ import annotations

import ast
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path

Rule = Callable[[ast.AST, Path], Iterator["Violation"]]


@dataclass(frozen=True, slots=True)
class Violation:
    path: Path
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line} {self.message}"


def scan(rule: Rule, roots: Iterable[Path]) -> list[Violation]:
    found: list[Violation] = []
    for root in roots:
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            found.extend(rule(tree, path))
    return found


def assert_clean(rule: Rule, roots: Iterable[Path]) -> None:
    violations = scan(rule, roots)
    if violations:
        raise AssertionError("\n" + "\n".join(str(v) for v in violations))


def calls(tree: ast.AST) -> Iterator[tuple[ast.Call, str]]:
    """호출 노드와 그 점 표기 이름. `self.session.commit()` → 'self.session.commit'."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            yield node, dotted_name(node.func)


def dotted_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = dotted_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def is_dataclass(node: ast.ClassDef) -> bool:
    return any("dataclass" in dotted_name(_decorator_target(d)) for d in node.decorator_list)


def _decorator_target(node: ast.expr) -> ast.expr:
    return node.func if isinstance(node, ast.Call) else node
