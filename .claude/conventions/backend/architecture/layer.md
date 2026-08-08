---
name: backend-architecture-layer
description: 새 파일을 어느 폴더에 둘지 정하거나 계층 간 import·의존 방향을 판단할 때 적용. layer-first 4계층(api·core·domain·infrastructure)의 경계와 조립 지점을 규정한다.
---
## Rule (폴더 = 계층)
- 최상위 패키지는 `app/`. 하위는 `api/`, `core/`, `domain/`, `infrastructure/` 4개만. 5번째 계층 신설 금지.
- 공용 유틸은 `app/shared/`에만. 도메인 지식이 들어가면 `domain/`으로 이동.
- 테스트는 `tests/unit/`(core·domain) + `tests/integration/`(api·infrastructure) 2층.

## Rule (의존 방향 — 단방향)
- 허용: `api → core → domain`, `infrastructure → domain`, `main.py → 전부`.
- 금지: `domain → 무엇이든`, `core → api`, `core → infrastructure`, `infrastructure → core`.
- `core`가 외부 시스템을 쓸 때는 `domain/repository.py`·`domain/ports.py`의 Protocol을 인자로 받는다. 구현체를 직접 import하지 않는다.
- 구현체를 Protocol에 꽂는 조립(wiring)은 `app/main.py`와 `app/api/deps.py`에서만 한다.

## Rule (계층별 허용 import)
- `domain/` — stdlib만. `dataclasses`, `enum`, `datetime`, `typing`, `abc` 수준.
- `core/` — stdlib + `domain`. `fastapi`·`sqlalchemy`·`spidev`·`firebase_admin` 전부 금지.
- `api/` — `fastapi`, `pydantic`, `core`, `domain`(타입 인용). SQLAlchemy 금지.
- `infrastructure/` — 외부 라이브러리 자유 + `domain`. `core`·`api` 금지.

## Rule (계층 간 데이터 타입)
- HTTP 경계 타입(Pydantic)과 도메인 타입(dataclass)과 영속 타입(SQLAlchemy)은 각각 별개 클래스다. 하나를 세 곳에 재사용하지 않는다.
- 변환 위치: Pydantic↔domain은 `api/`에서, ORM↔domain은 `infrastructure/db/repositories.py`에서.
- `core`의 입출력은 domain 타입 또는 원시 타입. Pydantic 모델을 인자로 받지 않는다.

## Rule (검증 명령)
- `rg "^(from|import) (fastapi|sqlalchemy|pydantic|spidev|firebase)" app/domain/` → 결과 0이어야 함.
- `rg "^(from|import) (fastapi|sqlalchemy)" app/core/` → 결과 0이어야 함.
- `rg "^from app\.(core|api)" app/infrastructure/` → 결과 0이어야 함.

## Anti-pattern
- `domain/`에 Pydantic `BaseModel` 사용 (dataclass 사용)
- `core/` 서비스 시그니처에 `Depends(...)` 또는 `Session` 등장
- 라우터 함수 안에서 `select(...)`·`session.add(...)` 직접 호출
- ORM 클래스에 비즈니스 메서드 부착 (그건 domain 모델)
- `infrastructure/`가 `core/` 서비스를 import해 역방향 호출
- 계층 안 두는 게 애매하다고 `app/utils/`에 로직 투기
- `main.py`에 endpoint 함수 직접 정의
- 순환 import 회피를 위한 함수 내부 지역 import (계층 위반 신호)
