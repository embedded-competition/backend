---
name: save-decision
description: |
  ADR 작성/갱신 + 인덱스 3종 sync 1트랜잭션. 부분 실패 시 통째 rollback.
  트리거: "ADR 저장", "decision log", "결정 기록", "save-decision", "ADR 영구화", "ADR commit", "결정 남겨".
  비-트리거: ADR 본문 작성(plan-system-design), 단발 git commit(git-commit), task-finalize(상위 호출자).
inputs:
  - "adr_draft_path: <worktree>/docs/decisions/<NNNN>-<slug>.md (필수)"
  - "decision_root: 작업 checkout root (default: adr_draft_path 기준 상위 root 추론)"
  - "status: draft | active | abandoned | superseded (필수)"
  - "warn_findings: [{priority, what}] (선택, PASS_WITH_WARN 시)"
  - "project_map_delta: [{op: add|remove|update, module, responsibility, entry_point}] (선택)"
  - "supersedes: [<NNNN>, ...] (선택)"
outputs:
  - "adr_final_path: docs/decisions/<NNNN>-<slug>.md"
  - "index_path: docs/decisions/index.md"
  - "project_map_path: docs/project-map.md"
  - "todos_path: <project>/TODOS.md"
  - "added_todos: [{priority, what}]"
triggers:
  - ADR 저장
  - decision log
  - 결정 기록
  - save-decision
  - ADR 영구화
not_for:
  - ADR 본문 작성 (plan-system-design)
  - 단발 git commit (git-commit)
  - task 전체 마무리 (task-finalize가 이 skill 호출)
---

# save-decision

ADR 파일 갱신 + decisions index + 선택적 project-map/TODOS를 1트랜잭션으로 sync한다. 부분 실패 시 전체 rollback.

## 사용 시점

- task-finalize의 squash merge 직전
- ADR 상태 변경 (draft→active, active→superseded, draft→abandoned)
- project-map 갱신이 필요한 task 완료 시

## 사전 조건

- ADR draft 파일이 존재하고 frontmatter 검증 통과
- `status` 파라미터 명시
- 모든 경로는 `decision_root` 기준으로 처리한다. `decision_root`가 없으면 `adr_draft_path`에서 repo root를 추론한다.

## 절차

### Step 1: frontmatter 검증

필수 필드 확인: name, status, task_id, branch, created, host.
실패 시: 거부 (rollback 불필요).

### Step 2: ADR status 갱신

```
adr_draft.status = <status>
adr_draft.decided_at = <오늘 날짜> (active/abandoned 시)
```

supersedes 명시 시:
```bash
# 기존 ADR status → superseded, superseded_by → 현재 task_id
sed -i 's/^status: .*/status: superseded/' docs/decisions/<PREV_NNNN>-*.md
# superseded_by: <NNNN> 추가
```

### Step 3: TODOS.md 갱신 (warn_findings 있을 때)

warn_findings → TODOS.md `## Followup` 섹션 P2/P3 항목 추가:
```markdown
### <NNNN>-followup: <what>
**What:** <what>
**Why:** PASS_WITH_WARN finding from task <NNNN>
**Context:** ADR docs/decisions/<NNNN>-<slug>.md Evidence 섹션 참조
**Effort:** S
**Priority:** P2
**Depends on:** None
```

`TODOS.md`가 없으면 아래 최소 골격을 먼저 만든다:

```markdown
# TODOS

## Followup
```

### Step 4: docs/decisions/index.md 재생성

```markdown
# ADR Index

| NNNN | slug | status | created | decided_at |
|---|---|---|---|---|
| 0001 | capability-refactor | active | 2026-05-10 | 2026-05-10 |
...
```

전체 재생성 (incremental 아님). 실패 시 rollback.

### Step 5: docs/project-map.md 갱신 (delta 있을 때)

project_map_delta 적용:
- op=add: 새 모듈 행 추가
- op=remove: 해당 모듈 행 삭제
- op=update: 기존 행 갱신

project-map.md 없으면 `.claude/skills/save-decision/templates/project-map.md` 골격으로 신규 생성.

### Step 6: 보고

```
save-decision 완료:
- ADR: docs/decisions/<NNNN>-<slug>.md (status: <status>)
- index: docs/decisions/index.md (갱신)
- project-map: docs/project-map.md (delta N개)
- TODOS: N개 항목 추가
```

## 오류 처리

- frontmatter 검증 실패: 거부 (파일 변경 없음)
- index 재생성 실패: rollback (ADR 상태 draft 복원)
- TODOS.md 형식 위반: rollback
- project-map 갱신 실패: 경고만 (TODOS/index rollback 안 함)

## 필수 artifact

- `docs/decisions/<NNNN>-<slug>.md` (status 갱신)
- `docs/decisions/index.md` (재생성)
- `TODOS.md` (P2/P3 추가, 해당 시)
- `docs/project-map.md` (delta 갱신, 해당 시)
