---
name: backend-config-tooling
description: ruff lint/format·mypy 타입체크 설정을 구성하거나 검사 게이트·무시 규칙을 다룰 때 적용.
---
## Rule (도구 구성)
- lint·format은 ruff 단일화. black·isort·flake8 병행 도입 금지 — 규칙 충돌로 포맷이 왕복한다.
- 타입 체크는 mypy. 설정은 전부 `pyproject.toml`에. `setup.cfg`·`.flake8`·`mypy.ini` 별도 파일 만들지 않는다.
- 도구 실행은 `uv run ruff ...`, `uv run mypy ...`. 전역 설치본 호출 금지.

## Rule (ruff)
- `[tool.ruff] target-version`을 `requires-python`과 일치시킨다.
- 규칙 세트는 최소 `E`(pycodestyle), `F`(pyflakes), `I`(import 정렬), `UP`(pyupgrade), `B`(bugbear), `ASYNC`(async 오용).
- `ASYNC` 규칙을 켠다 — async 함수 안 blocking 호출이 이 프로젝트의 실제 위험이다.
- `ruff format`을 포맷터로 쓴다. CI는 `ruff format --check`로 검사만.
- `# noqa`는 규칙 코드와 사유 주석을 함께 적는다. 벌거벗은 `# noqa` 금지.

## Rule (mypy)
- `[tool.mypy] strict = true`. 모든 public 함수에 인자·반환 타입.
- 서드파티 스텁이 없어 실패하는 모듈만 `[[tool.mypy.overrides]]`로 `ignore_missing_imports`를 켠다. 전역으로 켜지 않는다.
- `# type: ignore`는 코드와 사유를 함께 적는다: `# type: ignore[arg-type]  # spidev 스텁 없음`.
- `Any` 반환·인자는 경계(외부 SDK 래핑)에서만. domain·core에 `Any`가 들어오면 타입이 무의미해진다.
- `cast()`로 타입 검사를 우회하기 전에 실제 변환 함수를 쓸 수 있는지 먼저 본다.

## Rule (게이트)
- 커밋 전 로컬 검사 순서: `ruff check` → `ruff format --check` → `mypy` → `pytest`.
- CI에서 같은 순서로 돌린다. 로컬과 CI 명령이 달라지지 않게 `pyproject.toml`의 스크립트 또는 `Makefile`에 고정한다.
- lint 실패를 남긴 채 병합하지 않는다. 규칙이 과하면 규칙을 고치지, 무시를 늘리지 않는다.

## Anti-pattern
- ruff와 black 동시 사용
- 도구 설정이 `pyproject.toml` 밖 여러 파일에 분산
- `mypy` strict를 끈 채 타입 힌트만 형식적으로 부착
- 전역 `ignore_missing_imports = true`
- 사유 없는 `# noqa`·`# type: ignore`
- domain·core 시그니처에 `Any`
- `cast()` 남용으로 실제 타입 불일치 은폐
- 로컬 검사 명령과 CI 명령이 다름
- lint 실패를 "나중에" 남긴 채 병합
