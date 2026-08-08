---
name: shared-task-flow
description: 이슈 발급부터 branch·code·PR·review·merge·close까지 task 전체 lifecycle을 진행할 때 사용. 가장 바깥 entry point.
---
## 목적
**모든 작업의 시작은 이슈 티켓**이라는 원칙을 강제하는 task 전체 lifecycle. 이슈 발급 → branch → code → PR → review → merge → close까지 한 흐름.

본 워크플로우가 가장 바깥 entry point. 코드 작성 절차 자체는 `workflows/code.md`로 위임.

## 절대 원칙
- **모든 작업 = 이슈 티켓 발급부터 시작**
- 이슈 없이 branch·commit·PR 금지
- 예외 단 1개: 시연 중 장애 긴급 복구는 branch·PR 없이 main 직커밋 허용, 24h 내 이슈 사후 작성

## 7 단계 lifecycle

### 1. 이슈 발급
- 4 type template 중 택1 (`.github/ISSUE_TEMPLATE/`):
  - `bug` — 재현 가능한 버그 (재현 절차·환경·로그 필수)
  - `feature` — 새 기능 (시나리오·완료 기준 필수)
  - `chore` — 리팩터·인프라·문서·테스트 (목적·범위·완료 기준)
  - `decision` — 결정 질문 (옵션·책임자·기한)
- title: `<type>(<scope>): <subject>` (`git/issue.md` + `git/commit.md` 형식 일관)
- 기본 label: `type:<x>` + `status:triage`
- convention: `git/issue.md`

### 2. triage (1~2 영업일 내)
- 우선순위 label 부여: `prio:p0/p1/p2`
- assignee 지정
- 작업 범위 확인 (1 이슈 = 1 작업 단위. 크면 sub-task 분해 또는 epic + child)
- 라벨 갱신: `status:triage` → `status:ready`
- 분기 판단:
  - DB 변경 포함 → `workflows/migration.md` 의무
  - 새 Bounded Context → `workflows/add-context.md`
  - 새 Python pipeline → `workflows/add-python-pipeline.md`
  - 결정 필요 → `workflows/poc.md` 선행
  - 그 외 일반 → step 3 진행

### 3. branch 생성
- main에서 분기 (다른 feature branch에서 분기 금지 — `git/branch.md`)
- 명명: `<type>/<short-topic>-<issue-id>` 권장 (`feat/floor-polygon-binding-42`)
- 또는 `<type>/<short-topic>` (issue-id 생략 시 commit/PR에 `Refs #42` 명시)
- worktree 사용 권장 (`git/worktree.md`)
- assignee가 `status:ready` → `status:in-progress` 라벨 갱신

### 4. 코드 작성
- `workflows/code.md` 8단계 따름 (Karate → domain → UseCase → Repository → adapter → Controller → green → 로깅/메트릭)
- 모든 commit:
  - Conventional Commits (`git/commit.md`)
  - signed (`git/signing.md`)
  - 이슈 번호 참조 (`feat(mapping): bind floor polygon (#42)` 또는 footer `Refs #42`)
- 작업 중 blocker 발생 시 이슈에 `status:blocked` + 원인 코멘트
- 분기별 추가 절차:
  - DB 변경 → `workflows/migration.md` (Expand-Contract 3-PR)
  - 새 Python pipeline → `workflows/add-python-pipeline.md` 13단계
  - 새 context → `workflows/add-context.md` 10단계

### 5. PR open
- title: 이슈 title과 일관 (squash merge 후 commit subject가 됨)
- body 템플릿: `.github/pull_request_template.md`
- body 필수 필드:
  - **Summary** (1~3 bullet)
  - **Why** + `Closes #<issue-id>` 또는 `Refs #<issue-id>`
  - **Changes** (변경 layer)
  - **Test Plan** (단위/Karate/수동)
  - **Migration / Breaking** (없으면 "없음")
  - **Checklist** (6 axis self-check)
- draft → ready for review (self-review 후)
- convention: `git/pr.md`

### 6. review
- 6 axis (도메인 일관성·테스트·convention·migration 안전·secret·observability)
- convention: `workflows/code-review.md`, `git/review.md`
- 코멘트 prefix: `nit:` / `q:` / `suggest:` / `blocker:`
- author 24h 응답
- blocker 0 + 1+ approval + CI green + CODEOWNERS 매칭 → merge 가능
- 변경 종류별 추가 reviewer (migration → DBA, auth → security owner 등)

### 7. merge + close
- **squash merge** (fast-forward 깔끔, `git/branch.md`)
- PR body의 `Closes #N`이 이슈 자동 close
- branch 삭제 (remote + local)
- assignee가 issue 상태 확인 후 `status:in-progress` label 제거 (자동 close되면 생략)
- 후속:
  - main merge → `workflows/cicd.md` 자동 dev 배포
  - SemVer tag 시점에 `workflows/release.md` prod promote

## 분기 의사결정 (이슈 type → workflow)

| 이슈 type | 추가 workflow |
|---|---|
| `feature` (단순) | `code` → 일반 흐름 |
| `feature` + DB 변경 | `code` + `migration` |
| `feature` + 새 context | `add-context` → `code` |
| `feature` + 새 Python pipeline | `add-python-pipeline` → `code` |
| `bug` | `code` (회귀 테스트 필수) |
| `chore` (refactor/docs/test) | `code` (테스트 green 유지) |
| `chore` (infra/dependency) | `code` + 영향 영역의 docker/build convention |
| `decision` | `poc` → 결정 → ADR 작성 → 별 feature 이슈로 구현 |

## 1인 프로젝트 self-review
- self-approve 금지
- 24h 쿨다운 후 의식적 재읽기
- 6 axis 체크리스트를 PR 코멘트로 명시 (자기 검토 흔적)
- 협업자 추가 시 일반 절차로 전환

## blocked 처리
- 외부 의존 대기·결정 대기 시 `status:blocked` label + 원인·해소 책임자 코멘트
- 1주 이상 blocked → 이슈 우선순위 재평가 또는 분할

## 30일 idle 정책
- triage·ready·blocked가 30일 idle이면 stale 처리
- 우선순위 재확인 후 close 또는 백로그 이동
- in-progress가 30일 idle이면 assignee와 확인 (작업 포기 또는 분할)

## 금지
- 이슈 없이 branch·commit·PR 생성 (hotfix 외)
- 이슈 1개에 무관한 여러 작업 묶기
- PR body에 이슈 번호 누락 (`Closes #N` / `Refs #N`)
- triage 누락한 채 in-progress 진입
- assignee 없는 in-progress
- blocker 미해결 merge
- self-approval (1인 self-review는 시간차·코멘트 체크리스트 의무)
- merge 후 이슈 close 누락 (Closes #N으로 자동화)
- branch 삭제 누락
- `--no-verify` 우회
- 무관한 scope creep (별 이슈로 분리)

## 인용 관계
- 이슈 작성 정책: `git/issue.md`
- branch: `git/branch.md`
- commit: `git/commit.md`, `git/signing.md`
- 코드 작성: `workflows/code.md`
- PR: `git/pr.md`, `.github/pull_request_template.md`
- review: `workflows/code-review.md`, `git/review.md`
- 분기 절차: `workflows/{backend/migration,backend/add-context,shared/poc}`
