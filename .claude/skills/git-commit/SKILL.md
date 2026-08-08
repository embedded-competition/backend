---
name: git-commit
description: Git 커밋을 만들 때 사용 — diff 있는 변경, diff 없는 기록(plan·eval·ADR)의 empty commit, 피처 squash landing까지. 모든 커밋에 조회용 trailer 인덱스를 박고 squash 시 결정 전문을 집계한다. "커밋", "commit", "커밋해줘", "변경사항 정리", "plan/eval/adr 기록", "squash landing" 트리거. 비-트리거 — push/PR 생성, rebase·amend·cherry-pick 실행, commit history 조회.
---

# git-commit

## Purpose
- 어떤 커밋이 최종 history에 어떤 의미로 남는지 구분해 커밋한다.
- diff 없는 작업(plan·eval·ADR)도 마크다운 없이 empty commit으로 남긴다.
- 모든 커밋에 조회용 trailer 인덱스를 박고, squash landing 시 결정 전문을 집계한다.
- 커밋 형식 규칙은 보유하지 않는다 — 해당 규칙을 로드해 따른다.

## Inputs
- `working_dir` — git repo/worktree (기본 cwd).
- `mode` — standalone | diffless | cycle | landing (미지정 시 s1에서 판정).
- `intent` — 의도 설명 (subject·body 작성용).
- `pathspecs` — stage 대상 (있으면 우선).
- `feature` — `<id>-<slug>` (cycle/landing/피처 작업 시).
- `agent` — 커밋 주체 (trailer).
- `base` — squash 대상 base ref (landing 시).

## Modes
| mode | 언제 | history 의미 | diff |
|---|---|---|---|
| standalone | 일반 커밋 | main에 직접 | 있음 |
| diffless | plan·eval·ADR 기록 | branch evidence(squash로 집계) / ADR은 전문 carry | 없음 (`--allow-empty`) |
| cycle | 피처 branch 중간 checkpoint | branch 내부, squash로 사라짐 | 있음 |
| landing | 피처 → main squash merge | main에 1피처=1커밋 | squash index |

## Workflow

### s0 Validate input — precondition
- working_dir가 git repo/worktree인지, branch가 의도와 맞는지 확인.
- diffless·landing 외 모드는 stage할 변경이 있는지 확인.
- 충족 → s1
- 누락·불명 → 호출자에 반환

### s1 Determine mode
- mode가 주어졌으면 그대로.
- diff 없고 plan/eval/adr 의도 → diffless
- base + 피처 branch squash 의도 → landing
- 피처 branch 중간 checkpoint → cycle
- 그 외 → standalone

### s2 Stage (diff 있는 모드: standalone·cycle)
- pathspecs 있으면 그것만 `git add -- <pathspecs>`. `git add .`·`-a` 금지.
- unrelated dirty·staged change는 건드리지 않는다. 섞였으면 중단하고 분리 보고.
- `git diff --cached --stat` + `git commit --dry-run`으로 범위 확인. 의도와 다르면 중단.

### s3 Compose message
- 로드된 규칙(commit·ADR 형식)을 적용: `<type>(<scope>): <subject>`.
- trailer 인덱스를 footer에 둔다 — **trailer 앞에 빈 줄 필수** (없으면 git이 trailer로 인식 안 함).
  - `Agent:` · `Phase:` · `Feature: <id>-<slug>` · `ADR: <id>-<slug>` · `Verdict:` (값에 slug 필수, 맨 id 금지).
- diffless: body가 곧 기록 — plan 전문·eval 근거·ADR 전문(Context/Decision/Consequences/Alternatives).
- `bash {skill_dir}/scripts/check-message.sh <msg-file>`로 검증.
- landing·diffless는 `git interpret-trailers --parse <msg-file>`로 trailer가 읽히는지 확인.

### s4 Commit
- standalone·cycle → `git commit -F <msg-file>`.
- diffless → `git commit --allow-empty -F <msg-file>`.
- landing →
  - squash index 준비 (`git merge --squash <feature>` 또는 동등).
  - 본문 = `bash {skill_dir}/scripts/assemble-squash-body.sh <base> <feature>` (trailer 집계 + ADR 전문 carry, 결정적).
  - subject 한 줄 + 그 본문으로 `git commit -F <msg-file>`.
- trailer는 `--trailer "Key:value"`로 넣어도 됨 (빈 줄 자동 처리).

### s5 Confirm & report
- standalone·landing → 메시지 + staged stat 보여주고 승인받는다.
- cycle → caller 승인 주입됐으면 바로, 사람이 직접 요청한 cycle이면 확인.
- 보고 → `git rev-parse --short HEAD` + subject + mode.

## Constraints
- 커밋 형식 규칙을 복제하지 않는다 — 로드된 규칙 적용.
- `git add .`·`git commit -a` 금지 — pathspec·의도별만 stage.
- unrelated·user change를 커밋에 끌어들이지 않는다.
- trailer 값에 slug 없는 맨 id 금지 — 인덱스로 읽을 수 없다.
- trailer 앞 빈 줄을 보장한다 — 없으면 trailer 인식 실패.
- ADR을 마크다운 파일로 만들지 않는다 — diffless empty commit으로.
- squash landing 본문은 스크립트로 집계한다 — ADR 전문 carry 누락 금지.
- push·force·reset·amend는 범위 밖.
