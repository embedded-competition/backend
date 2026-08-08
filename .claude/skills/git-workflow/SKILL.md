---
name: git-workflow
description: 작업 하나를 이슈→branch→작업 단위 커밋→PR→리뷰→squash merge 흐름에 태울 때 사용. "이 작업 깃으로 진행", "이슈부터 시작", "브랜치 파고 작업", "커밋하면서 진행해줘", "PR 올려줘", "머지해줘" 트리거. 상황에 따라 단계를 생략하되 작업 단위 커밋은 생략하지 않으며, 커밋 body에 결정 근거를 남겨 나중에 log만으로 복원 가능한 history를 만든다. 비-트리거 — 커밋 1개만 작성(git-commit), worktree 격리 실행 흐름(feature-flow), 배포·릴리스(github-flow-deploy), 기존 로그 읽기(commit-ingest).
---

# git-workflow

## Purpose
- 작업을 git 흐름에 태워, 나중에 log만으로 무엇을·왜 했는지 복원 가능한 history를 남긴다.
- 단계는 상황에 따라 생략하되 작업 단위 커밋은 생략하지 않는다. squash landing은 커밋 다음 우선순위.
- 커밋·PR 형식 규칙은 보유하지 않는다 — 해당 규칙을 로드해 따르고, 문안 작성과 리뷰 판정은 전담 에이전트에 위임한다.

## Inputs
- `working_dir` — git repo/worktree (기본 cwd).
- `task` — 무엇을 구현·수정·결정할지.
- `feature` — `<id>-<slug>` (커밋 인덱스 키).
- `base` — 분기·landing 대상 ref (보통 main).
- `stages` — 실행할 단계 (미지정 시 s1에서 판정).

## Stages
| stage | 생략 조건 | 생략 시 대체 |
|---|---|---|
| issue | 원격·이슈 트래커 없음, 이미 티켓 있음 | 배경·완료 기준을 첫 커밋 body에 |
| branch | 이미 작업 branch 위 | 현재 branch 사용. base 위면 생략 금지 |
| commit | **없음 — 생략 불가** | — |
| PR | 원격 없음, 리뷰 대상 아님 | 로컬 squash landing |
| review | PR 없음 | 사용자 확인으로 대체 |
| squash merge | 커밋 history를 branch에 남길 이유가 명시적일 때만 | merge 없이 종료 (기본 아님) |

## Procedure

### s0 Validate input — precondition
- `working_dir`가 git repo/worktree인지, 현재 branch와 `base`가 의도와 맞는지 확인.
- `task`로 커밋 단위를 나눌 수 있는지 확인 — 무엇을 왜 바꾸는지가 없으면 커밋 body를 채울 수 없다.
- `feature` 식별자가 있거나 `task`에서 도출 가능한지 확인.
- 충족 또는 추론 가능 → s1
- 누락 & 추론 불가 → 정지·요구 (outcome = needs-input)

### s1 Scope stages
- 원격·이슈 트래커 가용성 확인 (`git remote -v`, 이슈/PR CLI 인증 상태).
- Stages 표로 실행할 단계를 확정하고 사용자에게 한 줄로 보고.
- 커밋 단계는 어떤 경우에도 생략 목록에 넣지 않는다.
- squash merge는 기본 포함 — 뺄 때만 이유를 확인받는다.

### s2 Issue (선택)
- type 택1 (bug|feature|chore|decision). title은 커밋 subject와 같은 형식.
- type별 필수 항목(재현 절차·시나리오·완료 기준·결정 옵션)을 채운다. 재료가 없으면 사용자에게 묻는다.
- 발급된 id를 이후 branch·커밋·PR 참조에 쓴다.
- 생략 → 배경과 완료 기준을 첫 커밋 body에 남긴다.

### s3 Branch (선택)
- `base`에서 분기한다. 다른 작업 branch에서 분기하지 않는다.
- 명명은 로드된 규칙에 따른다. 이슈 id가 있으면 포함.
- 이미 작업 branch 위면 생략. `base` 위면 생략 금지 — 분기 후 진행.

### s4 Commit — 필수·반복
- 작업 단위(1 논리 변경)마다 커밋한다. 한 커밋이 두 의도를 담게 되면 나눈다.
- 커밋 body에 무엇을 했는지 + 왜 그렇게 했는지 + 검토한 대안과 탈락 이유를 남긴다. WHAT만 적힌 body, 빈 body로 커밋하지 않는다.
- 문안(subject·body·trailer 인덱스)은 문안 전담 에이전트에 위임한다 — 전달은 `HANDOFF.md` 파일로 (subagent는 대화 컨텍스트 미상속). 전달 내용: 변경 diff 범위, `feature`, 이슈 id, 이번 단위에서 내린 결정과 대안.
- stage·commit 실행은 커밋 작성 절차에 위임한다 (trailer 인덱스·diff 없는 커밋·형식 검증 포함).
- diff 없는 작업(계획·결정·검증 결과)도 커밋으로 남긴다 — 마크다운 파일로 만들지 않는다.
- 본질 결정이 발생하면 결정 전문을 담은 diff 없는 커밋을 그 자리에서 남긴다 — 나중에 몰아 쓰지 않는다.
- 자력 복구 불가 실패(hook 실패 원인 불명, 해소 못 하는 충돌) → 정지·반환 (outcome = failed). 검사 우회로 통과시키지 않는다.

### s5 PR (선택)
- 원격 push 전에 사용자 승인을 받는다 — push는 비가역.
- PR title은 squash 후 subject가 되므로 커밋 subject 형식과 일치시킨다.
- body는 문안 전담 에이전트에 `HANDOFF.md`로 위임한다. 전달 내용: branch 커밋 목록, 이슈 id, 검증 방법, breaking 여부.
- 생성된 본문은 올리기 전 사용자가 1회 검수한다.
- 생략 → s7

### s6 Review (선택)
- 리뷰 판정 에이전트에 `HANDOFF.md`로 위임한다. 전달 내용: `base`, 변경 범위, PR 번호, 이번 작업의 완료 기준.
- 반환된 지적은 s4로 되돌려 커밋으로 반영한다 — 지적 반영도 작업 단위 커밋이다.
- blocker가 남은 채 진행하지 않는다.
- 통과 → s7

### s7 Land — postcondition
- 산출 전 아래를 확인:
  - 작업 단위 커밋이 남았고, 각 body에 무엇을·왜·검토한 대안이 적혔다.
  - 모든 커밋에 조회용 trailer 인덱스가 박혀 `git log --grep=`으로 조회된다.
  - 본질 결정이 diff 없는 커밋으로 남았다.
  - 이슈·PR을 썼다면 상호 참조가 연결됐다.
- 미충족 → s4
- 충족 → squash merge로 `base`에 landing한다. 본문은 branch 커밋의 trailer 집계 + 결정 전문 carry. merge 실행 전 사용자 승인(비가역).
  - squash 생략이 s1에서 확정된 경우에만 merge 없이 종료.
  - landing 후 branch 삭제·이슈 close를 확인한다. outcome = done

## Constraints
- 이 작업에 해당하는 규칙을 로드해 따른다 — 규칙 본문 미보유.
- 입력·산출 검증 실패 시 추측하지 않는다 — 정지·반환한다.
- 부분·미완 산출물을 내보내지 않는다 — 실패는 terminal 상태로 반환한다.
- 커밋 단계를 생략하지 않는다 — 다른 단계만 생략 가능하다.
- 커밋 body를 WHAT만으로 채우지 않는다 — 결정 근거 없으면 커밋하지 않는다.
- 결정을 마크다운 파일로 남기지 않는다 — diff 없는 커밋으로 남긴다.
- `git add .`·`commit -a`로 stage하지 않는다 — 무관한 변경을 커밋에 끌어들이지 않는다.
- push·merge·branch 삭제 등 비가역 동작은 사용자 승인 후 실행한다.
- 검사·정책 우회 플래그로 통과시키지 않는다.
- squash 본문에서 결정 전문 carry를 누락하지 않는다 — branch 소멸 시 결정이 함께 사라진다.
- subagent 전달을 prose로 하지 않는다 — `HANDOFF.md` 파일로 한다.
- 배포·릴리스, 코드 작성 절차 자체는 범위 밖이다.
