---
name: backend-architecture-service
description: app/core/ 아래 유스케이스 서비스를 작성하거나 트랜잭션 경계·Protocol 주입·서비스 분리 기준을 정할 때 적용.
---
## Rule (서비스 단위)
- 파일 1개 = 응집된 유스케이스 묶음 1개. `ingest_service.py`, `alert_service.py`, `device_service.py`.
- 서비스는 클래스로 만들고 의존은 `__init__`에서 Protocol 타입으로 받는다. 모듈 전역 상태 금지.
- 메서드 1개 = 유스케이스 1개. 이름은 동사구: `ingest_reading`, `acknowledge_alert`, `register_device`.
- 메서드가 40줄을 넘거나 분기 3단계를 넘으면 도메인 메서드 또는 private 헬퍼로 분해한다.

## Rule (입출력)
- 입력은 domain 타입 또는 원시 타입. Pydantic 모델을 받지 않는다.
- 출력은 domain 타입. HTTP 응답 형태로 가공하지 않는다 (그건 `api/`).
- 입력 인자가 4개를 넘으면 `@dataclass` command 객체로 묶는다.

## Rule (트랜잭션 경계)
- 트랜잭션 1개 = 유스케이스 메서드 1개. 서비스 메서드가 경계다.
- 세션 commit/rollback은 `api/deps.py`의 세션 의존성 또는 Unit of Work 래퍼가 담당한다. 서비스가 `session.commit()`을 직접 부르지 않는다.
- 외부 호출(FCM 푸시)은 DB 커밋 이후에 한다. 커밋 전 푸시하면 롤백 시 유령 알림이 나간다.
- 푸시 실패가 측정값 저장을 롤백시키지 않는다 — 실패는 로그 + 재시도 큐로 흘리고 유스케이스는 성공 처리한다.

## Rule (알람 파이프라인 특수)
- 노드가 이미 상태 판정(NORMAL/WATCH/ALARM/FAULT)을 마치고 올린다. 서버는 판정을 다시 하지 않는다 — 상태 전이 기록·중복 제거·알림 디스패치만 담당한다.
- 같은 이벤트가 LoRa 재전송으로 중복 도착할 수 있다. `(device_id, measured_at, seq)` 기준 멱등 처리한다.
- 상태가 직전 상태와 같으면 알림을 다시 보내지 않는다. 전이가 일어난 순간에만 디스패치한다.
- FAULT는 ALARM과 별개 경로로 통지한다. 감지 불능을 정상으로 뭉개지 않는다.

## Rule (에러)
- 서비스는 도메인 예외를 던지고 HTTP 상태를 모른다.
- 외부 시스템 실패는 `infrastructure/`에서 도메인 예외로 변환된 뒤 올라온다. 서비스에서 `httpx`·`sqlalchemy` 예외를 잡지 않는다.
- 예외를 삼키고 `None`을 반환하지 않는다.

## Anti-pattern
- `core/` 파일에 `from fastapi import Depends` 또는 `from sqlalchemy import select`
- 서비스가 구체 구현체(`FcmPushSender`, `SqlAlchemyReadingRepository`)를 직접 import
- 서비스 메서드가 Pydantic 요청 모델을 인자로 받음
- 서비스가 `session.commit()` 직접 호출
- 커밋 전에 푸시 발송
- 중복 프레임 멱등 처리 없이 그대로 insert
- 상태 변화 없는데 매 heartbeat마다 푸시 발송
- 서비스 안에서 `datetime.now()` 호출 (Clock port 사용)
- 유스케이스 하나가 여러 트랜잭션을 나눠 열고 부분 실패 상태를 남김
