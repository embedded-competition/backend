---
name: backend-framework-sqlalchemy
description: SQLAlchemy 2.0 ORM 모델·세션·엔진 설정을 작성하거나 SQLite 실행 옵션(WAL·PRAGMA·동시성)을 다룰 때 적용.
---
## Rule (2.0 스타일)
- 선언은 `DeclarativeBase` 상속 + `Mapped[...]` / `mapped_column(...)` 타입 애노테이션 방식.
- 조회는 `select(...)` + `session.execute(...)`. 레거시 `session.query()` 금지.
- ORM 클래스는 `app/infrastructure/db/orm.py`에만. 다른 계층에서 import 금지.
- ORM 클래스에 비즈니스 메서드·계산 프로퍼티를 붙이지 않는다. 데이터 매핑 전용.

## Rule (SQLite 엔진 설정)
- 파일 경로는 설정값. 메모리 DB는 테스트 전용.
- 부팅 시 PRAGMA 고정: `journal_mode=WAL`(동시 읽기), `synchronous=NORMAL`(SD카드 write 감소), `foreign_keys=ON`(FK 강제), `busy_timeout=5000`(락 대기).
- PRAGMA는 커넥션마다 적용돼야 한다 — `event.listens_for(engine, "connect")` 훅에서 실행한다. 한 번만 실행하면 새 커넥션에 안 걸린다.
- `check_same_thread=False`는 스레드풀 사용 시에만 켠다. 켤 거면 세션을 스레드 간 공유하지 않는다는 전제를 지킨다.
- 커넥션 풀은 작게. 워커 1개 + 수신 task 1개 구조에서 큰 풀은 메모리 낭비.

## Rule (SQLite 동시성 — 단일 writer)
- SQLite는 쓰기 직렬화된다. 쓰기 경로는 LoRa 수신 task 하나로 모은다. 여러 곳에서 동시 쓰기를 시도하면 `database is locked`가 난다.
- 쓰기 트랜잭션은 짧게. 트랜잭션 안에서 외부 호출(FCM)·긴 계산 금지.
- 읽기 전용 경로(API 조회)는 WAL 덕에 쓰기와 병행 가능하다. 조회에서 쓰기 트랜잭션을 열지 않는다.

## Rule (세션)
- 세션 수명 = 요청 1개 또는 유스케이스 1개. `app/api/deps.py`의 제너레이터 의존성에서 열고 닫는다.
- 백그라운드 수신 task는 요청 세션을 재사용하지 않는다. 자기 세션을 프레임 처리 단위로 열고 닫는다.
- 세션을 모듈 전역·클래스 속성으로 보관하지 않는다.
- `expire_on_commit=False`로 두고, 커밋 후 ORM 객체를 계속 쓰지 않는다 — repository에서 domain 객체로 변환해 반환한다.

## Rule (스키마 정의)
- 시계열 테이블은 `(device_id, measured_at)` 복합 인덱스 필수. 조회가 항상 장비 + 시간 범위이기 때문.
- 멱등 삽입용 유니크 제약을 둔다: `UNIQUE(device_id, measured_at, seq)`.
- 시각 컬럼은 UTC 저장. 로컬 시간 저장 금지.
- 부동소수 센서값은 `Float`. 금액·카운터가 아니므로 `Numeric` 불필요.
- `Base.metadata.create_all()`은 테스트에서만. 운영 스키마는 Alembic이 소유한다.

## Anti-pattern
- `session.query(...)` 레거시 API
- ORM 클래스에 도메인 로직·`to_dict()` 부착
- ORM 객체를 API 응답으로 직접 반환
- PRAGMA를 앱 시작 시 1회만 실행 (connect 이벤트 사용)
- `foreign_keys` PRAGMA 미설정으로 FK가 조용히 무시됨
- 쓰기 트랜잭션 안에서 FCM 호출
- 여러 task가 동시에 쓰기 트랜잭션 (`database is locked`)
- 전역 세션 객체
- 운영에서 `create_all()`로 스키마 생성 (Alembic 우회)
- 시계열 테이블에 인덱스 없이 시간 범위 조회
