---
name: shared-git-pr
description: Pull Request를 작성·리뷰·머지할 때 적용한다.
---

## Rule
- PR title은 squash merge 후 commit subject가 된다. Conventional Commits 형식 따름 (`feat(mapping): floor polygon binding`).
- PR body 템플릿:
  - **Summary**: 1~3 bullet. 변경의 핵심.
  - **Why**: 동기·배경 (PRD/ADR/issue link).
  - **Changes**: 주요 변경 영역 (선택).
  - **Test Plan**: 검증 방법 (단위·Karate·수동).
  - **Refs**: ADR ID, issue, 관련 PR.
- 1 PR = 1 논리 변경. 무관한 변경 분리.
- **1 PR = 1 Flyway migration 최대** (CLAUDE.md forbidden). DDL과 백필도 분리.
- PR 크기 가이드: 변경 라인 < 400 권장. 초과 시 분할.
- merge 방식: **squash merge** 통일.
- merge 전 필수: CI green + 리뷰 승인 1+ + main 동기화.
- breaking change는 body 상단 명시 + footer `BREAKING CHANGE:`.
- draft PR로 일찍 열어 가시성 확보. ready for review는 자체 검토 후.
- 리뷰 코멘트는 24h 내 응답 권장.
- PR 자동 생성 시 본문은 사람이 1회 검수 후 push.

## Anti-pattern
- 1 PR에 무관한 변경 묶기
- 1 PR에 Flyway migration 2개 이상 (CLAUDE.md forbidden)
- PR body 없이 merge
- "fix" 같은 vague title
- CI fail 상태로 merge 강행
- 리뷰 승인 없이 merge (긴급 hotfix는 별도 정책 + 사후 PR)
- 코드 외 자동 생성 파일을 PR로 따로 안 묶고 섞기
- breaking change를 footer 누락한 채 머지
- merge 후 브랜치 방치
- PR description에 비밀값/내부 URL 노출
- `--admin` 또는 강제 merge로 정책 우회
