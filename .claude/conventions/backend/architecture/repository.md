---
name: backend-architecture-repository
description: app/domain/repository.py Protocol 선언과 app/infrastructure/db/ 구현체를 작성하거나 ORM↔domain 변환·쿼리 위치를 정할 때 적용.
---
## Rule (Protocol 선언)
- Protocol은 `app/domain/repository.py`에 둔다. 이름은 `<Aggregate>Repository`.
- 메서드 시그니처에 domain 타입만. `Session`·ORM 클래스·`select()` 결과 노출 금지.
- 메서드는 유스케이스가 실제 필요로 하는 것만. 범용 `find_all()`·`query()` 만들지 않는다.
- 조회 결과 없음은 `None` 반환 또는 도메인 예외. ORM `NoResultFound`를 올리지 않는다.

## Rule (구현체)
- 구현체는 `app/infrastructure/db/repositories.py`. `__init__(self, session: Session)`로 세션 주입.
- 구현체가 ORM↔domain 변환을 소유한다. 변환 함수는 같은 파일 또는 `mappers.py`.
- ORM 클래스(`app/infrastructure/db/orm.py`)와 domain dataclass는 별개 타입. ORM에 도메인 메서드 부착 금지.
- 쿼리는 SQLAlchemy 2.0 스타일(`select(...)` + `session.execute(...).scalars()`). 레거시 `session.query()` 금지.

## Rule (쿼리 위치)
- 모든 SQL/ORM 쿼리는 repository 구현체 안에서만. 서비스·라우터에 쿼리 조각이 새면 계층 위반.
- 페이징은 repository 인자로 받는다(`limit`, `offset` 또는 커서). 전체 로드 후 파이썬 슬라이싱 금지.
- 시계열 조회는 항상 시간 범위 + 상한을 요구한다. 무제한 조회 메서드를 만들지 않는다 — RPi 메모리에서 전체 로드는 OOM 경로다.

## Rule (쓰기)
- 대량 삽입은 `session.execute(insert(...), [...])` batch. 루프 안 `session.add()` + 매번 flush 금지.
- 멱등 삽입은 SQLite `INSERT ... ON CONFLICT DO NOTHING` 사용. 조회 후 분기(check-then-act)는 경쟁 조건.
- `commit`은 repository가 하지 않는다. 트랜잭션 경계는 서비스 호출 단위(deps의 세션 스코프).

## Anti-pattern
- Protocol 메서드가 `Session`·`Select`·ORM 타입을 시그니처에 노출
- 서비스·라우터에서 `select(...)` 직접 작성
- ORM 클래스를 그대로 API 응답으로 반환 (lazy load 폭발 + 계층 누수)
- ORM 클래스에 비즈니스 메서드
- repository 안에서 `session.commit()` 호출
- 시간 범위·상한 없는 전체 조회 메서드
- 루프 안 `session.add()` + `flush()` 반복 (batch 사용)
- 조회 후 없으면 insert (check-then-act — upsert 사용)
- `session.query()` 레거시 API
