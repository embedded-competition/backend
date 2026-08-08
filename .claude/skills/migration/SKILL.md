---
name: migration
description: DB 스키마를 무중단·롤백 가능하게 바꿀 때 트리거. "스키마 변경", "컬럼 추가/삭제", "마이그레이션 작성", "테이블 변경 배포", "무중단 스키마", "Expand-Contract", "백필", "index 추가 배포" 의미면 사용. 비-트리거 — migration 파일 단순 조회, 코드 기능 구현, 배포 파이프라인 자체 셋업, 코드 리뷰 단독 수행.
---

# migration

## Purpose
- DB 스키마 변경을 무중단·롤백 가능(forward-only Expand-Contract)하게 수행한다.

## Procedure

### s0 Validate input — precondition
- 변경 대상 스키마 요소(테이블·컬럼)와 변경 종류(add / backfill / drop / NOT NULL 강제 / index)가 식별 가능해야 한다.
- 영향받는 Aggregate와 read·write 경로(UseCase)를 식별할 수 있어야 한다.
- migration 파일 저장 위치와 로컬 검증 수단(flyway migrate, 통합 테스트)에 접근 가능해야 한다.
- 충족 또는 추론 가능 → s1
- 누락 & 추론 불가 → 정지·요구 (outcome = needs-input)

### s1 변경 영향 분석
- 어떤 Aggregate가 영향 받나 식별한다.
- read·write 경로(UseCase)를 식별한다.
- rollback 시나리오를 정한다.

### s2 migration 파일 작성
- `src/main/resources/db/migration/V<seq>__<desc>.sql` 로 작성한다.
- 적용 규칙을 로드해 따른다.
- idempotent (`IF NOT EXISTS` 등) 하게 작성한다.
- DDL과 백필을 분리한다 — 한 파일에 섞지 않는다.
- index 추가는 별 PR로 분리하고, transactional 외 명령(`CREATE INDEX CONCURRENTLY`)을 일반 migration에 섞지 않는다.

### s3 로컬 검증
- flyway migrate를 실행한다.
- 신규 코드 동작을 통합 테스트로 확인한다 (green).
- 자력 복구 불가 실패 → 정지·반환 (outcome = failed)

### s4 PR 분할 결정
- 단순 add (NULLable): 1 PR.
- 백필 필요: 2-3 PR로 분할.
- destructive (drop·NOT NULL): 3 PR (Expand → Backfill → Contract).
- 분기 — destructive 변경은 3-PR 분할:
  - Expand: 새 컬럼/테이블 추가(NULLable). 기존 코드 동작 유지.
  - Backfill: 기존 데이터를 새 컬럼에 채움. 신규 코드 배포는 backfill 완료 후.
  - Contract: 미사용 컬럼/테이블 제거, NOT NULL 강제. 이전 컬럼 read/write 코드는 이 시점에 다 제거.
- 큰 데이터 백필(SQL 30초 초과) → chunked update (`WHERE id BETWEEN ... LIMIT ...`). 백필 중 lock 모니터링.

### s5 각 PR commit + review
- 적용 규칙을 로드해 review를 수행한다.
- migration PR은 추가 reviewer(DBA 또는 backend 시니어)를 둔다.

### s6 배포 순서 검증 — postcondition
- 산출 전 아래를 확인:
  - 1 PR = 1 migration 최대.
  - 이미 배포된 migration은 수정하지 않고 새 migration으로 보정한다.
  - 모든 변경이 두 단계 배포 가능하다 (역호환 → 마이그레이션 → 신규 코드).
  - 각 단계에서 직전 버전과 호환됨이 확인됐다.
  - 데이터 손실 risk 있는 destructive는 백업 확인 후 적용한다 (`pg_dump` 또는 snapshot).
  - prod 적용 전 dev에서 정확히 같은 순서로 검증됐다.
- 미충족 → 이전 상태
- 충족 → Expand 배포 → 검증 → Backfill → 검증 → Contract 순서로 배포한다. outcome = done

## Constraints
- 이 작업에 해당하는 규칙을 로드해 따른다 — 규칙 본문 미보유.
- 입력·산출 검증 실패 시 추측하지 않는다 — 정지·반환한다.
- 부분·미완 산출물을 내보내지 않는다 — 실패는 terminal 상태로 반환한다.
- forward-only 원칙. revert는 새 migration으로 한다 (추가한 컬럼 drop 등).
- 1 PR에 migration 2개를 넣지 않는다.
- DDL과 백필을 한 파일에 넣지 않는다.
- 신규 코드와 DDL을 같은 PR에 넣지 않는다 (Expand 누락 금지).
- destructive를 backfill과 한 PR에 넣지 않는다.
- 환경별로 다른 migration을 적용하지 않는다.
- repair를 일상적으로 사용하지 않는다.
- 백업 없이 destructive 변경을 적용하지 않는다.
- transactional 외 명령(`CREATE INDEX CONCURRENTLY`)을 일반 migration에 섞지 않는다.
