---
name: backend-framework-fastapi
description: FastAPI 앱 구성·lifespan·미들웨어·예외 핸들러·백그라운드 task를 작성하거나 앱 부팅 순서를 다룰 때 적용.
---
## Rule (앱 구성)
- `app/main.py`는 앱 인스턴스 생성 + lifespan + 미들웨어 + 예외 핸들러 등록 + `include_router`만. endpoint 정의 금지.
- 앱 생성은 팩토리 함수 `create_app() -> FastAPI`로 감싼다. 테스트가 설정을 바꿔 앱을 다시 만들 수 있어야 한다.
- 모듈 import 시점에 DB 연결·SPI 열기 같은 부작용을 일으키지 않는다. 전부 lifespan 안으로.

## Rule (lifespan)
- `@asynccontextmanager` lifespan 하나에서 자원 수명을 관리한다. deprecated `@app.on_event` 금지.
- 시작 순서: 설정 로드 → DB 엔진 → 마이그레이션 상태 확인 → LoRa 라디오 open → 수신 task 생성.
- 종료 순서는 역순. 수신 task는 `task.cancel()` 후 `await asyncio.gather(task, return_exceptions=True)`로 회수.
- 백그라운드 task 참조를 지역 변수로만 두지 않는다(GC로 사라짐). `app.state`에 보관한다.

## Rule (백그라운드 수신 루프)
- LoRa 수신은 `asyncio.create_task`로 뜬 장수 task. 요청 스코프의 `BackgroundTasks`와 구분한다.
- 루프 안 예외는 반드시 잡아 로그 남기고 계속 돈다. 예외로 task가 죽으면 수신이 조용히 멈춘다.
- 예외로 죽는 경우를 대비해 task에 `add_done_callback`으로 사망 로그를 남긴다.
- 루프는 취소 가능해야 한다 — `asyncio.CancelledError`는 잡아서 삼키지 말고 정리 후 재전파.

## Rule (미들웨어)
- 미들웨어는 request id 부여 + 요청/응답 로그 1줄 + 처리 시간 측정. 그 이상 넣지 않는다.
- 인증 미도입 상태이므로 CORS는 앱 origin만 명시 허용. `allow_origins=["*"]`와 `allow_credentials=True` 동시 사용 금지.
- 미들웨어에서 요청 body를 통째로 읽지 않는다(스트림 소진).

## Rule (예외 핸들러)
- `app/api/exception_handlers.py`에 도메인 예외 → HTTP 상태 매핑을 모은다.
- `RequestValidationError` 핸들러를 재정의해 응답을 `schema.md`의 단일 에러 형식으로 통일한다.
- 마지막 방어선으로 `Exception` 핸들러를 두되, 응답에는 요청 id만 노출하고 상세는 로그로.

## Rule (RPi 자원 제약)
- 워커 프로세스는 1개. `uvicorn --workers 1`. 512MB에서 다중 워커는 메모리 낭비 + SQLite 쓰기 경합.
- `uvicorn`은 `--loop asyncio` 기본 사용. `uvloop`은 ARM 빌드 부담 대비 이득이 작으면 도입하지 않는다.
- 응답에 대용량 배열을 담지 않는다. 시계열은 페이징 필수.

## Anti-pattern
- `main.py`에 endpoint 함수 정의
- `@app.on_event("startup")` 사용 (lifespan 사용)
- 모듈 최상단에서 `engine = create_engine(...)` 즉시 실행
- 백그라운드 task를 지역 변수로만 잡아 GC로 소멸
- 수신 루프에서 예외 미처리로 task 조용히 사망
- `CancelledError`를 `except Exception`으로 삼킴
- `allow_origins=["*"]` + `allow_credentials=True`
- `--workers 4` 같은 다중 워커 (512MB)
- 예외 응답에 스택트레이스 노출
