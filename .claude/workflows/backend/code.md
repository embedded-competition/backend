---
name: backend-code
description: 새 기능·수정을 코드로 옮길 때 따르는 outside-in BDD + DDD 4 layer 적층 절차.
---
## 목적
새 기능·수정을 코드로 옮길 때 따르는 절차. **outside-in BDD** + DDD 4 layer 적층.

## 순서 (CLAUDE.md `_project_meta.coding_principles.bdd` 부합)
1. **Karate feature 작성** (`src/test/resources/karate/<context>/<usecase>.feature`)
   - 외부 동작 명세. 시나리오 3~5개. red 상태 OK.
   - convention: `framework/karate.md`
2. **domain 모델 작성/수정** (`src/main/.../contexts/<context>/domain/`)
   - Aggregate Root·VO·Domain Service·Repository interface·Port interface
   - convention: `architecture/domain/*`, `framework/jpa.md`, `code/oop.md`
3. **UseCase 작성/수정** (`application/`)
   - Command/Query/Result inner record + UseCase 클래스 + `@Transactional`
   - convention: `architecture/application/*`, `framework/springboot.md`
4. **Repository 메서드 추가** (필요 시)
   - Spring Data 메서드명 또는 Custom 인터페이스 → infrastructure에 구현
   - convention: `architecture/domain/repository.md`, `architecture/infrastructure/persistence.md`
5. **infrastructure adapter 작성/수정** (필요 시)
   - Python adapter / 외부 API client. port 구현
   - convention: `architecture/infrastructure/*`, `python/protocol.md` (Python 시)
6. **Controller 작성** (`ui/`)
   - Request DTO → Command 변환, Result → Response 변환
   - convention: `architecture/ui/*`, `framework/springboot.md`
7. **Karate green 확인 → JUnit 단위 테스트 보강** (도메인 invariant·edge case)
   - convention: `framework/junit.md`
8. **로깅·메트릭 보강** (UseCase 진입·완료, 예외)
   - convention: `observability/observability.md`, `framework/logback.md`

## 분기 (변경 종류별 추가 절차)
- DB schema 변경 → `workflows/migration.md`
- 새 Bounded Context → `workflows/add-context.md`
- 새 Python pipeline → `workflows/add-python-pipeline.md`
- 새 외부 API → security/auth + credentials 절차 + ADR

## 항상 적용
- 1 PR 1 논리 변경 (`git/pr.md`)
- Conventional Commits (`git/commit.md`)
- cleancode·oop (`code/cleancode.md`, `code/oop.md`)
- secret leak 차단 (`git/gitignore.md`, `security/security.md`)

## 완료 기준 (Definition of Done)
- Karate feature green
- 단위 테스트 추가/통과
- spotless 통과
- PR description 6 axis 자기 검토 (`git/review.md`)
- migration 있으면 Expand-Contract 두 단계 분리 (`framework/flyway.md`)
- 영향 ADR/glossary 동기화
