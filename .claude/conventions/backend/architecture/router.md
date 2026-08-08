---
name: backend-architecture-router
description: app/api/ 아래 FastAPI 라우터·의존성·예외 핸들러를 작성하거나 endpoint 경로·상태 코드를 정할 때 적용.
---
## Rule (라우터 구성)
- 리소스 1개 = 파일 1개. `app/api/v1/devices.py`, `readings.py`, `alerts.py`.
- 각 파일은 `router = APIRouter(prefix="/devices", tags=["devices"])`로 시작. `main.py`가 `include_router(router, prefix="/api/v1")`로 조립.
- URL은 복수형 명사 + 소문자 + 하이픈: `/api/v1/devices/{device_id}/readings`. 동사 금지(`/getDevice` X).
- 버전은 경로에 박는다(`/api/v1`). 헤더 버전 협상 안 쓴다.

## Rule (핸들러 본문)
- 핸들러가 하는 일 3가지뿐: 요청 스키마 → domain/원시 타입 변환, 서비스 호출, 결과 → 응답 스키마 변환.
- 핸들러 본문 15줄 이내. 넘으면 로직이 새어든 것.
- 비즈니스 분기(`if state == AlertState.ALARM: ...`) 금지. 서비스로 내린다.
- 응답은 `response_model=` 명시. dict 직접 반환 금지.

## Rule (상태 코드)
- 조회 200, 생성 201(+`Location` 헤더), 본문 없는 성공 204.
- 검증 실패 422(Pydantic 기본), 인증 401, 권한 403, 없음 404, 상태 충돌 409.
- 상태 코드를 핸들러에서 `HTTPException`으로 흩뿌리지 않는다. 도메인 예외 → 상태 코드 매핑은 `app/api/exception_handlers.py` 한 곳.

## Rule (의존성)
- `Depends` provider는 `app/api/deps.py` 한 파일에 모은다. 라우터 파일마다 세션 팩토리 만들지 않는다.
- 서비스 인스턴스도 `deps.py`에서 조립해 주입한다: `def get_alert_service(session = Depends(get_session)) -> AlertService`.
- 테스트는 `app.dependency_overrides`로 교체하고 teardown에서 `clear()`.

## Rule (동기/비동기)
- 라우터는 `async def` 기본. 내부에서 blocking 호출(`spidev`, 동기 SQLite, `time.sleep`)을 직접 하지 않는다.
- blocking이 불가피하면 `fastapi.concurrency.run_in_threadpool` 또는 해당 핸들러를 `def`(동기)로 선언해 FastAPI가 스레드풀로 넘기게 한다.
- LoRa 수신 루프는 요청 흐름이 아니라 `lifespan`에서 뜨는 백그라운드 task로 관리한다. 라우터가 소유하지 않는다.

## Rule (lifespan)
- 시작/종료 자원(엔진, LoRa 라디오, 수신 task)은 `contextlib.asynccontextmanager` lifespan에서 열고 닫는다.
- 종료 시 수신 task를 `cancel()` + `await`으로 회수한다. 방치된 task 금지.

## Anti-pattern
- 라우터 안 `select(...)`·`session.add(...)`·`session.commit()`
- 핸들러가 `HTTPException(404)`을 도메인 판단으로 직접 던짐 (핸들러 매핑 사용)
- `response_model` 없이 dict·domain 객체 반환 (직렬화·문서 둘 다 깨짐)
- 모든 endpoint를 `main.py`에 평탄 등록
- 라우터 파일마다 `SessionLocal()` 직접 생성
- `async def` 핸들러에서 `requests`·`time.sleep` 사용
- URL에 동사, camelCase, 언더스코어
- 예외를 `except Exception: return {"error": ...}`로 삼켜 200 반환
