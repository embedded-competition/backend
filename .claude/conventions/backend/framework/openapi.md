---
name: backend-framework-openapi
description: Swagger/OpenAPI 명세를 작성·노출하거나 앱 클라이언트와 API 계약을 공유·동기화할 때 적용. 명세는 코드에서 생성하며 별도 yaml을 손으로 쓰지 않는다.
---
## Rule (명세의 출처)
- OpenAPI 문서는 FastAPI가 코드에서 생성한다. `openapi.yaml`을 손으로 작성해 병행 관리하지 않는다 — 코드와 어긋나는 순간 계약이 거짓말이 된다.
- 앱 클라이언트(별도 repo)와의 계약 공유는 생성된 `openapi.json`을 산출물로 커밋해서 한다. 생성 명령을 `scripts/dump_openapi.py`로 고정.
- API 변경 PR은 재생성한 `openapi.json` diff를 포함한다. diff가 비어 있으면 계약 변경 없음이 증명된다.

## Rule (문서 품질 — 앱 개발자가 읽고 구현 가능해야)
- 모든 endpoint에 `summary`(한 줄) + `tags` 필수. `description`은 동작이 자명하지 않을 때만.
- 응답은 `response_model` + `status_code` 명시. 성공 외에 발생 가능한 에러 상태는 `responses={404: {"model": ErrorResponse}}`로 선언.
- 요청·응답 스키마 필드에 `Field(description=..., examples=[...])`로 예시를 준다. 센서 값·타임스탬프처럼 형식 오해가 잦은 필드는 예시 필수.
- 라우터 `tags`는 리소스명 소문자 복수형으로 통일(`devices`, `readings`, `alerts`).
- deprecated endpoint는 `deprecated=True`로 표시하고 대체 경로를 `description`에 적는다. 조용히 삭제하지 않는다.

## Rule (노출)
- Swagger UI는 `/docs`, ReDoc은 `/redoc`, 원본은 `/openapi.json`.
- 인터넷에 터널로 노출되므로 운영 환경에서 문서 경로 노출 여부는 설정값(`ENABLE_DOCS`)으로 제어한다. 코드에 하드코딩하지 않는다.
- 인증 도입 시 `security_schemes`를 명세에 반영한다 — 문서에 안 나오는 인증은 앱이 구현할 수 없다.

## Rule (호환성)
- 필드 추가는 하위 호환. 필드 삭제·이름 변경·타입 변경·필수화는 파괴적 변경이므로 `/api/v2`로 간다.
- 에러 `code` 문자열은 계약의 일부다. 값 변경은 파괴적 변경으로 취급한다.
- 파괴적 변경 시 앱 담당자에게 알린 기록을 PR 본문에 남긴다.

## Anti-pattern
- 손으로 쓴 `openapi.yaml`을 코드와 병행 유지
- `summary`·`tags` 없는 endpoint (문서에서 식별 불가)
- 에러 응답을 명세에 선언하지 않아 앱이 성공 경로만 구현
- `response_model` 생략으로 스키마가 빈 객체로 문서화
- 예시 없는 타임스탬프·센서 값 필드
- 필드 이름을 바꾸면서 같은 `/api/v1` 유지
- 문서 경로를 코드 분기(`if ENV == "prod"`)로 하드코딩
- 앱 팀에 스크린샷으로 API 설명 (명세 대신)
