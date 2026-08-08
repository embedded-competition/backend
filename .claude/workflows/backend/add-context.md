---
name: backend-add-context
description: 새 Bounded Context를 신설할 때 따르는 절차. 기존 context로 흡수가 불가능한 마지막 수단으로 사용.
---
## 목적
새 Bounded Context를 신설하는 절차. **마지막 수단**으로 사용.

## 원칙
- 응집도 우선. 새 기능은 **기존 context에 흡수** 시도가 먼저 (CLAUDE.md `_anchors.base_context_meta.growth_response`).
- context 신설은 ADR 필수.
- context 명명은 lowercase 단수형 (`order`, `mapping`).

## context 신설이 정당화되는 신호
| 신호 | 임계 |
|---|---|
| 기존 context의 UseCase 수 | > 15 |
| 기존 context의 Aggregate 수 | > 5 |
| 기존 context 폴더 전체 파일 수 | > 80 |
| 도메인 어휘 충돌 | 같은 단어가 서로 다른 의미 (`Floor` 두 종류) |
| 트랜잭션 경계 충돌 | 같은 context 안에서 일관성 경계가 갈라짐 |
| 변경 빈도 차이 | 한 context의 일부만 자주 변경, 다른 부분은 거의 안 변경 |
| 팀 책임 분리 | 다른 사람·팀이 소유 |

위 임계 도달해도 **sub-folder로 분리 먼저** 시도 (`domain/<sub>/`). sub-folder로 응집 안 되면 context 신설.

## 절차
1. **신설 정당화 ADR**
   - `docs/decisions/NNNN-bounded-context-<name>.md`
   - Context (왜 신설), Alternatives (왜 sub-folder로 안 되나), Decision, Consequences
   - convention: `docs/ard.md`
2. **glossary 등재**
   - 새 context의 도메인 용어 정의
   - 같은 단어가 다른 context와 의미 다르면 `<Context>.<Term>` prefix
   - convention: `docs/glossary.md`
3. **폴더 구조 생성**
   ```
   src/main/java/.../contexts/<context>/
     application/
     domain/
     infrastructure/
     ui/             # ui layer 도입 정책 따름
   src/test/resources/karate/<context>/
   ```
4. **boundary 정의**
   - 어떤 다른 context의 UseCase를 호출할지 명시 (ADR-003 부합)
   - 도메인/infrastructure import 금지 일관
5. **첫 UseCase 1개 작성**
   - 외부 노출되는 최소 행위 1개부터
   - convention: `workflows/code.md`
6. **Karate feature 1개**
   - 외부 동작 시나리오
7. **migration**
   - 새 Aggregate 테이블
   - convention: `workflows/migration.md`
8. **prompt/index.yml 갱신**
   - 새 context 경로 추가 + `_conventions`, `_workflows` 매핑
9. **prompt/CLAUDE.md 갱신** (필요 시)
   - 동적 로드 매트릭스에 새 context 패턴 추가
10. **PR**
    - PR description에 ADR ID 명시
    - reviewer는 architect 또는 관련 owner

## 도입 후 보호
- context 간 application service 직접 호출만 (ADR-003)
- domain/infrastructure 직접 import 금지 (PR review에서 검출)
- 다른 context의 Aggregate를 변경하는 트랜잭션 금지

## 금지
- ADR 없이 context 신설
- 기존 context의 sub-folder 분리 시도 안 하고 바로 신설
- 같은 도메인 용어가 두 context에 다른 의미 (glossary로 분명히 분리)
- 신설 context를 기존 context의 application import로 의존성 만들기 (UseCase 호출만 OK)
- 새 context에 trivial UseCase 1개만 두고 방치 (응집도 가짜)
- prompt/index.yml + CLAUDE.md 갱신 누락
