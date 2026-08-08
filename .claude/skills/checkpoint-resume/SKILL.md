---
name: checkpoint-resume
description: |
  세션 중단 후 재개·이어서 작업·다른 세션 회수 시 worktree + git state를 읽어 현재 위치를 정확히 잡고 user dirty change를 보존하는 skill. 별도 checkpoint 파일을 SSOT로 만들거나 신뢰하지 않는다 — staleness가 곧 회귀(이미 끝난 작업 재수행 / user 수정분 되돌림)다.
  트리거: "이어서", "재개", "resume", "어디까지 했지", "중단된 작업", "이전 세션 이어", "checkpoint 확인", "task NNNN 이어서", "지난 번에 하던 거", "어디까지 진행됐어".
  사용자가 그 단어 그대로 안 써도 "중간에 끊겼는데 이어가자" 의미면 사용 검토.
  비-트리거: 새 task 시작(worktree-isolate), task 마무리(task-finalize), 단순 commit 조회(Bash 직접), 단순 status 확인.
inputs:
  - "worktree_path: 재개 대상 worktree (선택, 미지정 시 cwd 또는 사용자 질의)"
  - "task_id: NNNN (선택, path에서 자동 파싱)"
outputs:
  - "task_id: NNNN"
  - "last_commit: {hash, subject, cycle, verdict}"
  - "dirty_files: [{path, status}]"
  - "next_action: <한 줄>"
triggers:
  - 이어서
  - 재개
  - resume
  - 어디까지 했지
  - 이전 세션 이어
  - checkpoint 확인
not_for:
  - 새 task 시작
  - task 마무리
  - 단발 commit 조회
  - 단발 status 확인
---

# checkpoint-resume

worktree + git이 task 상태 SSOT다. resume은 git state 읽고 user dirty change 보존하는 것으로 끝낸다.

## 사용 시점

- 세션이 중단됐다가 다시 시작될 때
- "어디까지 했지", "이어서 하자" 같은 호출
- 다른 host(Claude/Codex)에서 만든 worktree에 진입할 때
- harness가 phase agent를 재호출하기 전 컨텍스트 재확립

## 절차

### Step 1 — worktree 식별

```bash
git -C <wt> rev-parse --show-toplevel
```

`task_id`/`slug`는 path(`.worktrees/task/<NNNN>-<slug>/`)에서 파싱. worktree path 없으면 사용자에게 1회 질의.

### Step 2 — 마지막 cycle commit

```bash
git -C <wt> log -1 --format=fuller
```

message trailer에서 `cycle <K>` / `Eval: <verdict>` 읽기. 없으면 plain commit으로 취급.

### Step 3 — dirty change 탐지

```bash
git -C <wt> status --porcelain
git -C <wt> diff HEAD
```

비어있지 않으면 user 수정 후보로 분류. 자동 stash/reset 금지.

### Step 4 — 보조 자료

`<wt>/docs/tasks/<NNNN>-<slug>/execution_report.md` 있으면 cycle history만 참고. 없어도 진행. report를 1차 근거로 쓰지 않는다.

### Step 5 — 현재 요청 비교

사용자 현재 요청 vs 마지막 cycle 비교. 충돌 시 현재 요청 우선.

### Step 6 — 첫 보고

```
task <NNNN> cycle <K>, last commit <hash> (<subject>), dirty <N>파일.
다음: <액션>
```

2줄. 긴 보고 금지.

## 게이트

- dirty change → user 수정. 되돌리기 금지. 다음 cycle에 포함할지 user 1회 확인.
- 이미 commit된 작업 다시 요청 받음 → commit hash 확인 후 skip. 재수행 금지.
- worktree 부재·branch 손상 → user 한 줄 보고 + 처음부터 여부 확인.
- final 직전 최신 요청 재확인 — checkpoint 시점 이후 변경 가능.

## 금지

- 별도 checkpoint yaml/json 작성·신뢰 금지. git 외 SSOT 만들지 않는다.
- execution_report.md를 resume 결정 1차 근거로 사용 금지. cycle history 참고만.
- dirty change 자동 정리 금지.

## 산출물 경로

skill은 상태 보고만 한다. 산출물 파일 없음.

## 영역 외

- 새 task 시작 → `git-workflow` (이슈 → branch)
- task 마무리 → `git-workflow` (PR → squash merge)
- 단발 status/log 확인 → Bash 직접
