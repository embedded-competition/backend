---
name: backend-framework-pytest
description: pytest 단위·통합 테스트를 작성하거나 fixture·DB 격리·하드웨어 fake·async 테스트 구조를 다룰 때 적용.
---
## Rule (2층 구조)
- `tests/unit/` — `core`·`domain` 대상. 외부 의존 0, DB 0, 네트워크 0. 밀리초 단위로 끝나야 한다.
- `tests/integration/` — `api`·`infrastructure` 대상. 임시 SQLite + ASGI 클라이언트 사용.
- 공용 fixture는 `tests/conftest.py`, 층별은 `tests/<층>/conftest.py`.

## Rule (테스트 작성)
- 이름은 `test_<대상>_<조건>_<기대결과>`. `test_ingest_duplicate_frame_is_ignored`.
- 테스트 1개 = 시나리오 1개. Given/When/Then을 빈 줄로 구분한다.
- status만 검증하고 끝내지 않는다. 응답 body 필드까지 assert.
- 동일 endpoint 다중 케이스는 `@pytest.mark.parametrize`. 함수 복붙 금지.
- 테스트 간 실행 순서에 의존하지 않는다. 각 테스트는 단독 실행으로 통과해야 한다.

## Rule (DB 격리)
- 통합 테스트 DB는 `tmp_path` 기반 임시 SQLite 파일. 개발용 DB 파일을 건드리지 않는다.
- fixture에서 Alembic `upgrade head`로 스키마를 만든다 — 마이그레이션이 깨졌는지도 같이 검증된다.
- 테스트마다 트랜잭션 롤백 또는 새 파일로 초기화. 이전 테스트 데이터가 남지 않게.

## Rule (하드웨어·외부 fake)
- LoRa(SPI)·FCM은 domain Protocol의 fake 구현으로 대체한다. `tests/fakes/`에 둔다.
- 테스트 코드가 `spidev`·`firebase_admin`을 import하지 않는다. CI·Mac에 그 장치가 없다.
- fake는 `unittest.mock.Mock`보다 실제 클래스 구현을 선호한다 — Protocol 시그니처가 바뀌면 타입 체크로 잡힌다.
- 시간은 `Clock` port의 fake로 고정한다. `freezegun` 같은 전역 패치보다 주입이 낫다.

## Rule (async)
- `pytest-asyncio` 사용, `asyncio_mode = "auto"`를 `pyproject.toml`에 설정.
- API 통합 테스트는 `httpx.AsyncClient(transport=ASGITransport(app=app), base_url="http://test")`.
- lifespan을 타야 하는 테스트는 `LifespanManager` 또는 명시적 startup/shutdown 호출로 자원을 연다.

## Rule (의존성 override)
- 라우터가 쓰는 `Depends` provider를 `app.dependency_overrides[...]`로 교체한다.
- fixture teardown에서 `app.dependency_overrides.clear()`. 안 지우면 다음 테스트가 오염된다.

## Rule (실행·커버리지)
- 실행은 `uv run pytest`. 전역 pytest 호출 금지.
- 커버리지는 `pytest --cov=app`. `core`·`domain`이 커버리지의 의미 있는 부분이다 — 전체 수치만 보고 판단하지 않는다.
- 느린 테스트는 `@pytest.mark.slow`로 표시하고 기본 실행에서 제외 가능하게 한다.

## Anti-pattern
- `tests/` 평면 구조 (단위·통합 미분리)
- 단위 테스트가 DB·파일·네트워크 접근
- `assert r.status_code == 200` 단독 검증
- 테스트가 실행 순서에 의존 (앞 테스트가 만든 데이터 사용)
- 개발용 DB 파일을 테스트가 사용
- 테스트에서 `spidev`·`firebase_admin` import
- `dependency_overrides` 정리 누락
- `datetime.now()` 실제 시각에 의존하는 단정
- 스키마를 `create_all()`로 만들어 마이그레이션 검증을 건너뜀
- 한 테스트에서 생성·조회·수정·삭제를 전부 검증
