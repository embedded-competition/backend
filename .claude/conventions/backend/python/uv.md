---
name: backend-python-uv
description: Python 의존성·가상환경·실행 설정을 작성·검토할 때 적용 (uv + pyproject.toml, uv.lock commit, uv run 실행)
---
## Rule
- Python 의존성 관리는 **uv + pyproject.toml** 단일화. requirements.txt 신규 도입 X.
- 각 pipeline 폴더(`python/<pipeline>/`)에 `pyproject.toml` + `uv.lock`. lock 파일은 commit.
- entry point는 `pyproject.toml`의 `[project.scripts]` 또는 `main.py` 둘 다 허용 (ADR-009).
- Python 버전은 `pyproject.toml`의 `requires-python = ">=3.12"` 같이 명시.
- 의존성 추가: `uv add <pkg>` (자동 lock 갱신). 직접 pyproject.toml 편집 후 `uv sync` 도 OK.
- 개발 의존성은 `uv add --dev <pkg>`. test/lint/format은 dev로 분리.
- 의존성 install: `uv sync --frozen` (lock 정확히 적용). CI 필수.
- venv는 `uv venv` (자동 `.venv/` 생성). `.venv/`는 `.gitignore`.
- Python script 실행은 `uv run python <script>` 또는 `uv run <entry-script>`. system python 직접 호출 X.
- 의존성 audit: `uv pip list --outdated`, `uv tree`로 의존성 그래프 점검.
- ML model 패키지(torch, opencv 등)는 base image에서 미리 install 권장 (docker/base.md 참조). pyproject에는 명시만.
- `pip install` 직접 호출 금지 (uv 우회).

## Anti-pattern
- requirements.txt 신규 도입 (uv lock 사용)
- system python 직접 (`python3 script.py` — `uv run` 사용)
- lock 파일 commit 누락
- pyproject.toml에 wildcard version (`*`)
- 의존성 직접 install (`pip install`) — uv 경유
- `--no-frozen`으로 lock 무시 install (재현성 깨짐)
- venv 활성화 의존 (`source .venv/bin/activate` — `uv run` 사용)
- 도구별 다른 dependency manager 혼용 (poetry/pipenv/pip-tools 등)
- `.venv/` commit
- Python script에 비즈니스 로직 (CLAUDE.md forbidden — 입출력 JSON 처리만)
- system pip로 dev tool install (`uv tool install`)
