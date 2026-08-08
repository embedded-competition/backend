---
name: shared-git-issue
description: GitHub Issue를 생성·라벨링·triage·종료할 때 적용한다.
---

## Rule
- 이슈는 GitHub Issues에서 관리한다. 작업·버그·결정 요청·문서 작업 모두 이슈로 시작.
- title 형식: `<type>(<scope>): <subject>` (commit.md와 동일 prefix). 예: `feat(mapping): floor polygon binding`, `bug(scan): chunk merge timeout`.
- type: `feat`, `bug`, `chore`, `docs`, `refactor`, `test`, `question`, `decision`.
- scope: Bounded Context 또는 layer (`mapping`, `scan`, `floor`, `infra`).
- body는 type별 템플릿(`.github/ISSUE_TEMPLATE/`)을 사용한다.
  - **Bug**: 재현 절차, 기대/실제 동작, 환경(profile/version), 로그 스니펫
  - **Feature**: 사용자 시나리오, 성공 기준, 관련 PRD/ADR link
  - **Chore**: 작업 목적, 완료 기준
  - **Decision**: 결정해야 할 질문, 옵션, 트레이드오프 → 결정 후 ADR 작성으로 close
- label은 3 축으로만:
  - **type**: `type:feat` / `type:bug` / `type:chore` / `type:docs` / `type:decision`
  - **priority**: `prio:p0` / `prio:p1` / `prio:p2` (p0=즉시, p1=이번 스프린트, p2=백로그)
  - **status**: `status:triage` / `status:ready` / `status:in-progress` / `status:blocked`
- 새 이슈는 기본 `status:triage`. 1~2 영업일 내 triage(분류·우선순위·assign) 처리.
- 이슈 1개 = 1 작업 단위. PR과 1:1 매핑되도록 분할. 큰 이슈는 sub-task list로 분해 또는 epic 이슈 + child 이슈.
- PR 본문에 `Closes #N` / `Refs #N`으로 자동 닫기/참조.
- 작업 시작 시 assignee 본인 설정 + `status:in-progress` 라벨.
- blocked 시 `status:blocked` + 차단 원인 코멘트 (외부 의존·결정 대기 등).
- 결정형 이슈는 결론을 ADR로 영구화 후 close. 이슈 본문에 ADR ID 역참조.
- 30일 idle 이슈는 자동/수동 stale 처리. 우선순위 재확인 후 close 또는 백로그.

## Anti-pattern
- 작업을 이슈 없이 시작 (가시성·history 손실)
- 1 이슈에 무관한 여러 작업 묶기
- 한글/공백 title (subject 한글은 OK, type/scope는 영문)
- label 남발 (3 축 외 label 추가는 ADR 또는 합의 필요)
- body 없이 title만 생성
- "fix bug" 같은 vague title
- bug 이슈에 재현 절차 누락
- decision 이슈를 ADR 없이 close
- assignee 없는 채로 in-progress 라벨
- 비밀값(.env, key, 내부 URL)을 이슈 본문/코멘트에 노출
- PR과 무관한 이슈를 강제 close (관련 PR merge로만 close)
- triage 누락한 채 1주 이상 방치
