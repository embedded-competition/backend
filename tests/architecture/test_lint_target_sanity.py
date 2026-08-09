"""규칙이 실제로 무언가를 겨냥하고 있는지 확인한다.

경로 오타 하나로 규칙 전체가 0개 파일을 스캔하고 조용히 통과한다.
템플릿을 옮길 때 가장 흔한 실패이고, 통과 로그만 보면 절대 드러나지 않는다.
"""

from __future__ import annotations

import re
import subprocess

from tests.architecture import lint_target as target

_MIN_ANALYSED_FILES = 50


def test_every_layer_path_contains_sources() -> None:
    for path in target.LAYERS:
        assert list(path.rglob("*.py")), f"LintTarget 경로가 비었다 — 규칙이 무검사 통과: {path}"


def test_rule_exception_paths_exist() -> None:
    """예외 경로가 사라지면 그 규칙은 정상 코드를 위반으로 신고하기 시작한다."""
    for path in (
        target.CONFIG_MODULE,
        target.ORM_MODULE,
        target.CLOCK_ADAPTER,
        *target.TRANSACTION_SCOPES,
    ):
        assert path.exists(), f"예외 경로가 없다 — LintTarget을 갱신할 것: {path}"


def test_import_linter_analyses_the_real_package() -> None:
    """`Analyzed 0 files`여도 import-linter는 모든 계약을 KEPT로 보고한다."""
    result = subprocess.run(
        ["uv", "run", "lint-imports"],  # noqa: S607
        capture_output=True,
        text=True,
        check=False,
        cwd=target.ROOT.parent,
    )
    match = re.search(r"Analyzed (\d+) files", result.stdout)
    assert match is not None, f"lint-imports 출력 형식이 바뀌었다:\n{result.stdout}"
    assert int(match.group(1)) >= _MIN_ANALYSED_FILES, (
        f"grimp가 {match.group(1)}개만 분석했다 — root_package 확인"
    )
