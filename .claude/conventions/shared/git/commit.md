---
name: shared-git-commit
description: Git 커밋 메시지를 작성하거나 커밋 단위를 나눌 때 적용한다. trailer 인덱스·diff 없는 작업의 empty commit·squash 집계 포함.
---

## Rule
- Conventional Commits 준수. 형식: `<type>(<scope>): <subject>`.
- type: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `build`, `ci`, `perf`, `style`, `plan`, `eval`, `adr`.
- scope: Bounded Context 또는 layer.
- subject: 명령형, 소문자 시작, ≤ 72자, 마침표 없음.
- body는 선택. WHY 위주. WHAT은 diff에 있음. (diff 없는 커밋은 body가 곧 기록 — 전문 작성)
- 1 commit = 1 논리 변경. 무관한 변경 섞기 금지.
- 한글 subject 허용하되 type/scope는 영문 유지.
- pre-commit hook 실패 시 `--no-verify` 우회 금지. 원인 해결 후 재시도.

## Trailer index
모든 커밋에 조회용 trailer를 둔다. 값은 `<id>-<slug>` (id=zero-pad 정렬·유일, slug=룩업 없이 읽히는 요약).
- `Agent: <agent-name>` — 이 커밋을 만든 주체.
- `Phase: plan|build|eval` — (있으면) 작업 단계. 단일 actor면 생략.
- `Feature: <id>-<slug>` — 소속 피처. 예: `Feature: 0042-worktree-isolation`.
- `ADR: <id>-<slug>` — 관련·기록 결정. 예: `ADR: 0012-empty-commit-decision-log`.
- `Verdict: pass|fail|needs-changes` — eval 커밋에만.
- `Deprecates: <id-slug>[, ...]` — 이 커밋이 obsolete시키는 과거 feature·ADR. ingest가 컨텍스트에서 제외.
- 조회: `git log --grep="^ADR:"`, `git log --grep="Feature: 0042"`, `git log --grep="Agent: <name>"`.

## Diff-less work
- plan·eval·ADR처럼 diff가 없는 작업은 `git commit --allow-empty`로 남긴다 — 마크다운 문서를 만들지 않는다.
- body가 곧 기록(plan 전문·eval 근거·ADR 전문). subject + trailer로 인덱싱.

## Squash landing
- 피처 branch를 main에 squash merge할 때 squash 본문은 branch 커밋들의 trailer를 집계한다 (Agent 목록·Feature·Verdict).
- ADR 커밋의 **전문(body)을 squash 본문에 carry**한다 — plan/eval 상세는 버리되 ADR 결정 근거는 영속.
- 집계는 결정적 스크립트로 한다 — 수동·harness·skill 무관 동일 결과.
- main에는 1 피처 = 1 커밋. branch의 plan/eval empty 커밋은 squash로 사라짐(집계 trailer만 남음).
- landing 시 과거 live feature·ADR을 검토해, 이 변경이 obsolete시키는 것에 `Deprecates: <id-slug>` trailer를 단다 — history 불변이라 옛 커밋을 못 고치고 forward로 선언한다. ingest가 deprecated를 컨텍스트에서 뺀다.

## Anti-pattern
- type 누락 또는 비표준 type (`update`, `change`, `fix-stuff`)
- subject에 마침표·이모지·이슈번호 직접
- 1 commit에 무관한 변경 묶기
- 의미 없는 메시지 (`WIP`, `fix typo`, `asdf`)
- subject > 72자
- body에 WHAT만 적기 (diff 중복)
- trailer 값에 slug 없이 맨 id (`ADR: 012`) — 인덱스로 읽을 수 없음
- diff 없는 작업을 마크다운 파일로 남김 (empty commit으로 해야 함)
- squash 시 ADR 전문 carry 누락 (branch만 보존했다 ADR 소실)
- 비밀값(.env, key) 포함 commit
- amend로 published commit 변경
- `--no-verify` 우회
