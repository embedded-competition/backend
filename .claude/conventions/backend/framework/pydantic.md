---
name: backend-framework-pydantic
description: Pydantic v2 모델·validator·pydantic-settings 설정 클래스를 작성하거나 환경변수 로딩·타입 강제 정책을 정할 때 적용.
---
## Rule (v2 API 고정)
- Pydantic v2만 사용. v1 호환 레이어(`pydantic.v1`) import 금지.
- 메서드: `model_validate`, `model_validate_json`, `model_dump`, `model_dump_json`, `model_copy`.
- 설정은 `model_config = ConfigDict(...)` 클래스 속성. 내부 `class Config` 금지.

## Rule (validator)
- 필드 단일 제약은 `Annotated[T, Field(...)]`로 선언. validator 함수로 대체하지 않는다.
- 값 정규화는 `@field_validator(mode="before")`, 필드 간 관계 검증은 `@model_validator(mode="after")`.
- validator에서 I/O(DB 조회·HTTP 호출) 금지. 순수 함수여야 한다 — 검증 계층에서 부작용이 나면 재시도·테스트가 깨진다.
- validator는 값을 반환한다. 예외를 삼키고 기본값으로 대체하지 않는다.

## Rule (pydantic-settings)
- 설정 클래스는 `app/core/config.py`의 `Settings(BaseSettings)` 하나. 모든 환경변수의 SSOT.
- `model_config = SettingsConfigDict(env_file=".env", env_prefix="APP_", extra="forbid")`. 알 수 없는 키는 즉시 실패시킨다.
- 필드에 타입과 기본값을 명시한다. 비밀값은 기본값을 주지 않는다 — 없으면 부팅이 실패해야 한다.
- 비밀 필드는 `SecretStr`. 로그·에러에 평문 노출을 막는다.
- `Settings`는 `@lru_cache`로 감싼 `get_settings()`로 접근. 모듈 전역 인스턴스를 여기저기 import하지 않는다.
- 코드 어디서도 `os.getenv` 직접 호출하지 않는다. 전부 `Settings` 경유.

## Rule (경계 전용)
- Pydantic 모델은 HTTP 경계(`app/api/schemas/`)와 설정(`app/core/config.py`)에서만 쓴다.
- `app/domain/`은 dataclass. Pydantic을 도메인 모델로 쓰지 않는다 — 검증 프레임워크가 도메인 불변식을 대신하면 규칙이 스키마에 흩어진다.
- LoRa 프레임 파싱 결과도 domain dataclass. Pydantic으로 받지 않는다.

## Anti-pattern
- `class Config:` 내부 클래스 (ConfigDict 사용)
- `.dict()`·`.json()`·`parse_obj`·`parse_raw` v1 메서드
- `@validator`·`@root_validator` v1 데코레이터
- validator 안에서 DB 조회·HTTP 호출
- `os.getenv("...")` 코드 산재
- 비밀값 필드에 기본값 제공 (`api_key: str = "changeme"`)
- 비밀값을 평문 `str`로 선언 (`SecretStr` 사용)
- `extra="allow"`로 오타 난 환경변수가 조용히 무시됨
- domain 모델을 `BaseModel`로 선언
