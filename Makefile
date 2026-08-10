.DEFAULT_GOAL := check

# 게이트를 사람 기억이 아니라 명령 하나에 둔다. CI도 같은 타깃을 부른다 —
# 로컬에서 통과한 것이 CI에서 다르게 도는 일이 없어야 한다.
.PHONY: check fix types imports arch style test contract deps deep dead mutants openapi

check: style types imports arch test deps

fix:
	uv run ruff check --fix .
	uv run ruff format .

style:
	uv run ruff check .
	uv run ruff format --check .

types:
	uv run mypy

imports:
	uv run lint-imports

arch:
	uv run pytest tests/architecture -q

test:
	uv run pytest --cov=app --cov-report=term-missing --cov-fail-under=90

deps:
	uv run deptry .

# 앱 팀과의 계약이 조용히 드리프트하지 않게 한다. 스펙이 바뀌었는데
# 재생성을 안 했으면 여기서 깨진다.
openapi:
	uv run python scripts/dump_openapi.py
	git diff --exit-code docs/openapi.json

# ---- 느린 층. 릴리스 전·주간 ------------------------------------------
deep: contract dead mutants

contract:
	uv run pytest tests/contract -q -m contract

dead:
	uv run vulture

mutants:
	uv run mutmut run
