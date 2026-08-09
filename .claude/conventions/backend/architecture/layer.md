---
name: backend-architecture-layer
description: 새 파일을 어느 폴더에 둘지, 한 파일에 무엇까지 담을지, 계층 간 import·의존 방향이 맞는지 판단할 때 적용. layer-first 5계층(api·runtime·core·domain·infrastructure)의 경계와 조립 지점, 모듈 분리 기준을 규정한다.
---
## Rule (폴더 = 계층)
- 최상위 패키지는 `app/`. 하위는 `api/`, `runtime/`, `core/`, `domain/`, `infrastructure/` 5개만. 6번째 계층 신설 금지.
- `runtime/` — 조립(composition root) + 비-HTTP 구동 어댑터(수신 루프 등). 라우터와 같은 "밖에서 안으로 부르는" 쪽이라 `infrastructure/`가 아니다.
- 공용 유틸은 `app/shared/`에만. 도메인 지식이 들어가면 `domain/`으로 이동.
- 테스트는 `tests/unit/`(core·domain) + `tests/integration/`(api·infrastructure) 2층. 테스트 폴더 구조는 대상 모듈 구조를 그대로 따라간다.

## Rule (의존 방향 — 단방향)
- 허용: `api → runtime → core → domain`, `infrastructure → domain`.
- 금지: `domain → 무엇이든`, `core → api`, `core → runtime`, `infrastructure → 상위 계층`.
- 구현체를 port에 꽂는 조립은 `app/runtime/wiring.py`·`providers.py`에서만 한다.
- 계층 방향은 `pyproject.toml`의 import-linter 계약이 SSOT다. 새 계층·새 예외를 만들면 계약도 같이 고친다.

## Rule (파일 분리 기준 — 크기가 아니라 변경 이유)
- 같은 이유로 함께 바뀌면 한 파일. 서로 안 부르고 따로 바뀌면 다른 파일. 줄 수는 판단 근거가 아니다.
- 한 클래스 한 파일로 쪼개지 않는다 — Python의 단위는 클래스가 아니라 모듈이다.
- **묶는 기준은 하위도메인이지 기술적 종류가 아니다.** "엔티티끼리", "Protocol끼리", "저장소끼리" 묶는 건 계층 안에 또 계층을 만드는 것이다.
- 쪼갠 뒤 서로 import하면 경계를 잘못 그은 것이다. `independence` 계약으로 못박아 회귀를 막는다.
- 다음은 쪼개지 않는다:
  - 값 객체와 그것만을 위한 보조 타입 (`TelemetryFrame` + `Coordinates`)
  - 계약값 카탈로그 — 중복·누락이 한눈에 보여야 하는 것 (예외 `code`, 상태 enum)
  - ORM 테이블 선언 — 모듈 import가 빠지면 Alembic autogenerate가 `DROP TABLE`을 낸다
- 패키지 `__init__.py`에서 re-export하지 않는다. 호출부가 실제로 쓰는 모듈만 import하게 둔다.

## Rule (계층별 허용 import)
- `domain/` — stdlib만. `dataclasses`, `enum`, `datetime`, `typing`, `abc` 수준.
- `core/` — stdlib + `domain` + 저장소 어댑터. `fastapi`·`sqlalchemy`·`spidev` 직접 import 금지.
- `api/` — `fastapi`, `pydantic`, `core`, `domain`(타입 인용). SQLAlchemy 금지.
- `runtime/` — 조립을 위해 모든 계층 허용.
- `infrastructure/` — 외부 라이브러리 자유 + `domain`. 상위 계층 금지.

## Rule (계층 간 데이터 타입)
- HTTP 경계 타입(Pydantic)과 도메인 타입(dataclass)과 영속 타입(SQLAlchemy)은 각각 별개 클래스다. 하나를 세 곳에 재사용하지 않는다.
- 변환 위치: Pydantic↔domain은 `api/`에서, ORM↔domain은 해당 저장소 모듈 안에서(비공개 함수).
- `core`의 입출력은 domain 타입 또는 원시 타입. Pydantic 모델을 인자로 받지 않는다.

## Rule (검증 명령)
- `uv run lint-imports` → `0 broken`이어야 함. grep이 못 잡는 전이 의존·순환 import까지 본다.
- 계약을 완화(`allow_indirect_imports`, 예외 모듈)할 때는 그 자리에 이유와 되돌릴 조건을 주석으로 남긴다.

## Anti-pattern
- `domain/`에 Pydantic `BaseModel` 사용 (dataclass 사용)
- `core/` 서비스 시그니처에 `Depends(...)` 또는 `Session` 등장
- 라우터 함수 안에서 `select(...)`·`session.add(...)` 직접 호출
- ORM 클래스에 비즈니스 메서드 부착 (그건 domain 모델)
- 수신 루프·스케줄러를 `infrastructure/`에 두고 거기서 `core` 서비스 호출 (→ `runtime/`)
- 파일이 길다는 이유만으로 분해, 또는 짧다는 이유만으로 병합
- 저장소끼리 서로 호출 (트랜잭션 경계가 흐려진다 — 조합은 서비스에서)
- 계층 안 두는 게 애매하다고 `app/utils/`에 로직 투기
- 순환 import 회피를 위한 함수 내부 지역 import (계층 위반 신호)
