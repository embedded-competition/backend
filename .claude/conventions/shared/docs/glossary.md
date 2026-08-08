---
name: shared-docs-glossary
description: 도메인 용어를 정의·등재하거나 용어/코드 이름을 동기화할 때 적용한다.
---
## Rule
- 도메인 용어집은 `docs/glossary.md`(또는 `docs/glossary/<context>.md` 분리)에 둔다.
- 1 용어 = 1 정의. 같은 개념을 다른 이름으로 부르지 않는다 (synonym 금지).
- 용어 항목 구조:
  - **Term**: 도메인 명사 (PascalCase 영문 + 한글 병기)
  - **Definition**: 1~2 문장
  - **Context**: 어느 Bounded Context의 용어인지 (`mapping`, `localize` 등)
  - **Examples**: 코드/시나리오 예시 (선택)
  - **Related**: 관련 용어 link (선택)
- 같은 단어가 context별 다른 의미면 context를 prefix로 명시 (`Mapping.Floor` vs `Building.Floor`).
- 도메인 객체(Aggregate Root, VO) 이름은 glossary 등재 권장.
- 외부 라이브러리 용어(`RTAB-Map`, `SuperPoint`, `LightGlue`)는 도구 섹션 분리.
- 용어 변경 시 코드·ADR·PRD에 일괄 반영 (search-replace + PR 리뷰).
- 신규 용어는 첫 등장 PR과 같이 등재.

## Anti-pattern
- 같은 개념의 동의어 양산 (`Building`/`Site`/`Place` 혼용)
- 용어 정의 없이 코드/문서에 도입
- WHAT만 적고 WHY/Context 누락
- 한 단어를 두 의미로 사용 (context 분리 또는 이름 재명명)
- glossary와 code 이름 불일치 (search-replace로 강제 동기화)
- 외부 도구명을 도메인 개념으로 혼용
- 정의에 다른 미정의 용어 사용 (순환/미해결 참조)
