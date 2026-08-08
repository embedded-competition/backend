---
name: shared-docs-prd
description: 새 feature/epic의 요구사항(문제·목표·시나리오)을 PRD로 명세할 때 적용한다.
---
## Rule
- PRD(Product Requirements Document)는 `docs/prd/<feature>.md`에 둔다.
- 1 PRD = 1 feature 또는 1 epic. 너무 큰 단위는 분할.
- 본문 구조:
  - `# <Feature>`
  - **Problem**: 사용자 pain / 비즈니스 동기
  - **Goal**: 측정 가능한 성공 기준 (지표·수치)
  - **Non-Goals**: 의도적으로 안 하는 것
  - **User Scenarios**: 핵심 사용 흐름 (3~5개 시나리오)
  - **Functional Requirements**: 시나리오에서 도출된 기능 목록
  - **Non-Functional Requirements**: 성능·보안·신뢰성·UX 제약
  - **Open Questions**: 미결정 사항 + 결정 책임자/기한
  - **References**: 관련 ADR·glossary·이슈 link
- 시나리오는 Karate feature와 1:1 매핑 가능한 단위로 작성 (외부 동작 명세).
- 측정 가능한 표현 (`P99 < 200ms`, `성공률 ≥ 99%`). 모호한 형용사 금지(`빠르게`, `안정적으로`).
- 도메인 용어는 glossary 등재 후 사용.
- PRD 갱신 시 변경 이력은 git history. 본문에 changelog 섹션 두지 않음.
- 구현 결정(어떤 library/패턴)은 PRD에 적지 않음 — ADR로.

## Anti-pattern
- 1 PRD에 여러 feature/epic 묶기
- 측정 불가능한 표현 (`빠르게`, `안정적`, `확장 가능`)
- 구현 detail (어떤 library·패턴) 포함 (ADR로)
- Non-Goals 누락 (범위 폭증 위험)
- glossary에 없는 용어 신규 도입 (먼저 등재)
- Open Questions에 책임자/기한 없는 항목 방치
- "이미 만들었다"는 사후 정당화 PRD (선행 작성 원칙)
- 시나리오 없이 기능 list만 (외부 동작 검증 불가)
