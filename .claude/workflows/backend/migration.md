---
name: backend-migration
description: DB 스키마 변경을 무중단·롤백 가능하게 수행할 때 따르는 forward-only Expand-Contract 절차.
---
## 목적
DB 스키마 변경을 무중단·롤백 가능하게 수행하는 절차. forward-only Expand-Contract 패턴.

## 핵심 원칙 (CLAUDE.md + framework/flyway.md)
- 1 PR = 1 migration 최대
- 이미 배포된 migration 수정 X (새 migration으로 보정)
- DDL과 백필 분리
- 모든 변경은 두 단계 배포 가능해야 함 (역호환 → 마이그레이션 → 신규 코드)

## 3-PR 분할 패턴 (destructive 변경 시)
1. **Expand PR**: 새 컬럼/테이블 추가 (NULLable). 기존 코드 동작 유지
   - migration: `V<seq>__add_<col>_to_<table>.sql` (NULL 허용)
   - 코드: 기존 동작 그대로 + 새 컬럼 read/write 가능
2. **Backfill PR**: 기존 데이터를 새 컬럼에 채움
   - migration: `V<seq>__backfill_<table>_<col>.sql`
   - 신규 코드 배포는 backfill 완료 후
3. **Contract PR**: 미사용 컬럼/테이블 제거. NOT NULL 강제
   - migration: `V<seq>__enforce_not_null_<table>_<col>.sql` 또는 `V<seq>__drop_<col>_from_<table>.sql`
   - 기존 코드(이전 컬럼 read/write)는 이 시점에 다 제거됨

## 절차
1. **변경 영향 분석**
   - 어떤 Aggregate가 영향 받나
   - read·write 경로 (UseCase) 식별
   - rollback 시나리오
2. **migration 파일 작성**
   - `src/main/resources/db/migration/V<seq>__<desc>.sql`
   - convention: `framework/flyway.md`
   - idempotent (`IF NOT EXISTS` 등)
3. **로컬 검증**
   - `./gradlew flywayMigrate`
   - 신규 코드 동작 확인 (Karate green)
4. **PR 분할 결정**
   - 단순 add (NULLable): 1 PR로 충분
   - 백필 필요: 2-3 PR로 분할
   - destructive (drop·NOT NULL): 3 PR
5. **각 PR commit + review**
   - convention: `workflows/code-review.md`
   - migration PR은 추가 reviewer (DBA 또는 backend 시니어)
6. **배포 순서 검증**
   - Expand 배포 → 검증 → Backfill → 검증 → Contract
   - 각 단계에서 prev 버전과 호환 확인

## 큰 데이터 백필 정책
- 백필 SQL 30초 초과 → chunked update (`WHERE id BETWEEN ... LIMIT ...`)
- 외부 도구(쿼리 worker) 사용 시 ADR
- 백필 중 lock 모니터링

## index 추가
- Postgres `CREATE INDEX CONCURRENTLY` 권장
- Flyway transactional 외 명령이므로 별도 처리 (`-- ${flyway:non-transactional}` 또는 manual)
- 별 PR (DDL과 분리)

## rollback 계획
- forward-only 원칙. 새 migration으로 revert (drop 추가한 컬럼 등)
- 데이터 손실 risk 있는 destructive는 백업 확인 후 (`pg_dump` 또는 snapshot)
- prod 적용 전 dev에서 정확히 같은 순서로 검증

## 금지
- 1 PR에 migration 2개
- DDL + 백필 한 파일
- 신규 코드 + DDL 같은 PR (Expand 누락)
- destructive를 backfill과 한 PR
- 환경별 다른 migration 적용
- repair 일상 사용
- 백업 없이 destructive
- transactional 외 명령(`CREATE INDEX CONCURRENTLY`)을 일반 migration에 섞음
