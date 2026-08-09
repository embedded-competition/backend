---
name: backend-architecture-domain
description: app/domain/ 아래 dataclass 도메인 모델·값객체·Protocol port를 작성하거나 불변식 위치를 정할 때 적용.
---
## Rule (모델)
- 엔티티는 `@dataclass`. 식별자 필드를 가지고 동등성은 식별자 기준.
- 값객체는 `@dataclass(frozen=True)`. 식별자 없고 값 전체로 동등.
- 원시값(`str`·`float`·`int`)이 도메인 의미를 가지면 값객체로 포장: `DeviceId`, `GasChannel`, `AlertState`.
- 상태 변경은 메서드로만. 필드 직접 대입을 호출자에게 허용하지 않는다.
- 불변식(invariant)은 생성 시점 `__post_init__` 또는 상태 변경 메서드 안에서 검증하고, 깨지면 도메인 예외를 던진다.

## Rule (도메인 예외)
- `app/domain/exceptions.py`에 도메인 예외를 정의한다. 베이스 1개(`DomainError`) + 구체 예외.
- 도메인 예외는 HTTP 상태 코드를 모른다. 매핑은 `api/`의 예외 핸들러에서 한다.
- 외부 라이브러리 예외(`sqlalchemy.exc.*`, `httpx.*`)를 domain까지 올리지 않는다. `infrastructure/`에서 도메인 예외로 변환한다.

## Rule (파일 배치)
- 하위도메인 단위로 파일을 나눈다 — `device.py`, `readings.py`, `alerting.py`, `access.py`, `push.py`. "엔티티 모음" 파일(`models.py`)을 만들지 않는다.
- 나눈 하위도메인끼리는 서로 import하지 않는다. 필요해지면 경계를 잘못 그은 것이므로 합치든 다시 긋든 결정한다 (import-linter `independence` 계약으로 강제).
- 값 객체와 그것만을 위한 보조 타입은 한 파일에 둔다 (`TelemetryFrame` + `Coordinates`).
- 예외는 `exceptions.py` 한 파일에 모은다 — `code`가 앱과의 계약이라 중복·누락이 한눈에 보여야 한다.

## Rule (Protocol port)
- `app/domain/ports/<port명>.py` — port 1개 = 파일 1개. 어댑터가 자기가 구현할 port만 import하게 한다.
- port는 구현이 2개 이상일 때만 만든다 (`FrameSource` fake/sx1276, `PushSender` logging/expo, `Clock` system/fixed). 저장소처럼 구현이 하나면 만들지 않는다.
- `ports/__init__.py`에서 re-export하지 않는다.
- `typing.Protocol` 사용. `ABC` 상속 강제 X (구현체가 domain을 import하지 않아도 되게).
- 시간은 `Clock` port로 주입한다. 도메인·서비스에서 `datetime.now()` 직접 호출 금지 (테스트 불가).

## Rule (센서 도메인 특수)
- 센서 채널·알람 상태는 `Enum`으로 고정: `GasChannel = {VOC, H2, CO, TEMP, HUMIDITY, PRESSURE, WATER}`, `AlertState = {NORMAL, WATCH, ALARM, FAULT}`.
- 노드가 보낸 상태 문자열을 그대로 저장하지 않는다. Enum 파싱 실패는 예외로 드러낸다.
- `ALARM`은 자동 해제하지 않는다 — 해제는 명시적 명령으로만 상태 전이 메서드를 호출한다.
- 측정 시각은 노드 시각(`measured_at`)과 서버 수신 시각(`received_at`)을 둘 다 보관한다. 하나로 합치지 않는다.

## Anti-pattern
- domain 파일에 `import fastapi`·`import sqlalchemy`·`import pydantic`
- 엔티티 필드를 호출자가 직접 대입 (`reading.state = "ALARM"`)
- 불변식 검증이 서비스에 흩어짐 (도메인 안으로)
- 값객체를 mutable dataclass로 선언
- `datetime.now()`·`time.time()` 도메인·서비스 직접 호출
- 도메인 예외에 `status_code` 필드 부착
- Enum 대신 문자열 리터럴 비교 (`if state == "ALARM"`)
- getter/setter만 있는 빈혈 도메인 (로직이 전부 서비스에)
