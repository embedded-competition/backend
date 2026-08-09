---
name: backend-architecture-repository
description: app/infrastructure/db/repositories/ 저장소 어댑터를 작성하거나 ORM↔domain 변환·쿼리 위치를 정할 때, 저장소 Protocol이 필요한지 판단할 때 적용.
---
## Rule (Protocol을 만들 시점)
- **구현이 하나면 Protocol을 만들지 않는다.** 타입 중복만 생기고 갈아끼울 대상이 없다.
- 두 번째 구현이 실제로 생길 때(캐시 레이어·읽기 전용 복제본·인메모리 대체) 그때 추출한다.
- 테스트가 실제 SQLite를 쓰면 fake 구현이 없으므로 Protocol 근거가 하나 더 사라진다.
- Protocol을 만든다면 메서드 시그니처에 domain 타입만. `Session`·ORM 클래스·`select()` 결과 노출 금지.
- 메서드는 유스케이스가 실제 필요로 하는 것만. 범용 `find_all()`·`query()` 만들지 않는다.
- 조회 결과 없음은 `None` 반환 또는 도메인 예외. ORM `NoResultFound`를 올리지 않는다.

## Rule (구현체)
- 저장소 1개 = 파일 1개. `app/infrastructure/db/repositories/<집합체>.py`.
- 세션은 `@dataclass(frozen=True, slots=True)`의 필드로 받는다. `__init__` 수기 작성 금지.
- ORM↔domain 변환 함수는 **그 저장소와 같은 파일에 비공개(`_`)로** 둔다. 유일한 호출자가 그 저장소이고, 컬럼 추가 시 두 파일을 오가지 않게 한다.
- 저장소끼리 서로 import하지 않는다. 여러 집합체를 엮는 건 서비스의 일이다(트랜잭션 경계).
- ORM 클래스(`app/infrastructure/db/orm.py`)와 domain dataclass는 별개 타입. ORM에 도메인 메서드 부착 금지.
- `orm.py`는 쪼개지 않는다 — 모듈 import가 빠지면 Alembic autogenerate가 그 테이블에 `DROP TABLE`을 낸다.
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
- 구현이 하나뿐인데 Protocol 선언 (타입 중복)
- 저장소 여러 개를 한 파일에 몰아넣기 (서로 안 부르는 것들이 같이 커진다)
- 변환 함수만 모은 `mappers.py` (호출자와 멀어져 컬럼 추가 때 두 파일을 오간다)
- 저장소가 다른 저장소를 호출
- Protocol 메서드가 `Session`·`Select`·ORM 타입을 시그니처에 노출
- 서비스·라우터에서 `select(...)` 직접 작성
- ORM 클래스를 그대로 API 응답으로 반환 (lazy load 폭발 + 계층 누수)
- ORM 클래스에 비즈니스 메서드
- repository 안에서 `session.commit()` 호출
- 시간 범위·상한 없는 전체 조회 메서드
- 루프 안 `session.add()` + `flush()` 반복 (batch 사용)
- 조회 후 없으면 insert (check-then-act — upsert 사용)
- `session.query()` 레거시 API
