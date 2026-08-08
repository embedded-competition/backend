---
name: backend-architecture-schema
description: app/api/schemas/ 아래 Pydantic 요청·응답 DTO를 작성하거나 도메인 모델과의 변환·필드 노출 범위를 정할 때 적용.
---
## Rule (DTO 분리)
- 요청과 응답은 별개 클래스. `DeviceCreateRequest`, `DeviceResponse`. 하나를 양쪽에 쓰지 않는다.
- DTO는 domain dataclass와 별개 타입. domain을 `response_model`로 직접 쓰지 않는다.
- 변환은 DTO 쪽 classmethod로: `DeviceResponse.from_domain(device)`. domain이 DTO를 아는 방향은 금지.
- 리소스 1개 = 스키마 파일 1개. `app/api/schemas/device.py`.

## Rule (Pydantic v2)
- `model_config = ConfigDict(strict=True)` 기본. 암묵 타입 강제 변환을 막는다.
- v2 API만 사용: `model_validate`, `model_dump`, `model_dump_json`. v1 `.dict()`·`.json()`·`parse_obj` 금지.
- 필드 제약은 타입에 박는다: `Annotated[float, Field(ge=0, le=100)]`, `Annotated[str, StringConstraints(min_length=1)]`.
- 응답 DTO는 `model_config = ConfigDict(from_attributes=True)`를 켜지 않는다 — ORM 자동 매핑은 계층 누수 경로다. 명시 변환을 쓴다.

## Rule (필드 노출)
- 응답에 내부 식별자·원시 센서 raw·디버그 필드를 습관적으로 싣지 않는다. 앱이 실제 쓰는 필드만.
- 시간 필드는 UTC aware `datetime`으로 직렬화(ISO 8601 + `Z`). naive datetime 금지.
- 열거값은 domain Enum을 그대로 노출하되 값은 안정적인 문자열(`"ALARM"`). 정수 코드 금지 — 앱 코드가 매직넘버로 오염된다.
- 페이징 응답은 `{items: [...], next_cursor: ...}` 형태로 감싼다. 최상위 배열 반환 금지(스키마 확장 불가).

## Rule (에러 응답 형식)
- 에러 응답은 전 endpoint 단일 형식: `{"code": "<DOMAIN_CODE>", "message": "<사람이 읽는 설명>", "detail": {...}}`.
- `code`는 도메인 예외 클래스와 1:1. 앱이 분기하는 값이므로 임의 변경 금지 — 변경은 API 버전 변경.
- `message`에 스택트레이스·SQL·파일 경로를 넣지 않는다.

## Anti-pattern
- 하나의 Pydantic 모델이 요청 DTO + 응답 DTO + ORM 매핑 3역
- domain dataclass를 `response_model`로 지정
- `from_attributes=True`로 ORM 객체 자동 직렬화
- `.dict()`·`.json()` v1 메서드 호출
- `strict=False`로 문자열 `"3"`이 `int 3`으로 조용히 통과
- naive `datetime` 응답 (타임존 없음)
- 최상위가 JSON 배열인 응답
- 에러 응답 형식이 endpoint마다 다름
- 응답에 센서 raw 배열 통째 노출 (대역폭·의미 둘 다 손해)
