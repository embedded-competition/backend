---
name: backend-observability-logging
description: 애플리케이션 로그를 작성·구성하거나 로그 레벨·구조화 필드·journald 보존·SD카드 write 정책을 다룰 때 적용.
---
## Rule (구조화 로그)
- 표준 `logging` 모듈 사용. 로거는 모듈별 `logger = logging.getLogger(__name__)`.
- 로그는 key=value 또는 JSON 구조. 문자열 보간으로 값을 문장에 녹이지 않는다 — 나중에 grep·집계가 안 된다.
- 지연 포맷을 쓴다: `logger.info("frame received", extra={...})`. f-string으로 미리 만들면 레벨이 꺼져도 비용이 든다.
- 필수 컨텍스트 필드: `request_id`(HTTP 경로), `device_id`(LoRa 경로), `alert_id`(알림 경로).
- `print()` 금지.

## Rule (레벨 기준)
- `DEBUG` — 개발 중 상세. 운영 기본 레벨에서 꺼진다.
- `INFO` — 상태 전이, 유스케이스 진입/완료, 부팅·종료, 라디오 초기화 결과.
- `WARNING` — 복구된 이상. CRC 실패, 중복 프레임, 재시도 성공, 노드 시계 편차.
- `ERROR` — 처리 실패. 파싱 실패, 푸시 최종 실패, DB 오류.
- `CRITICAL` — 서비스 지속 불가. 라디오 초기화 실패, DB 연결 불가.
- 예외 로그는 `logger.exception(...)`으로 스택을 남긴다. `logger.error(str(e))`는 원인을 지운다.

## Rule (RPi SD카드 write 제약)
- 애플리케이션이 파일에 직접 로그를 쓰지 않는다. stdout → journald가 표준 경로다.
- journald에 보존 상한을 건다: `SystemMaxUse=` 설정. 무제한 증가는 SD카드를 채우고 DB 쓰기를 막는다.
- `Storage=volatile`(램) 또는 상한을 건 persistent 중 택1. 결정을 `deploy/`에 문서화한다.
- 고빈도 이벤트(프레임 수신)를 프레임마다 INFO로 남기지 않는다. 카운터로 집계해 주기적으로 1줄 남긴다.
- 반복 로그는 억제한다 — 같은 오류가 초당 수십 줄 나면 원인 1줄이 묻히고 카드 write만 늘어난다.

## Rule (민감 정보)
- 비밀값·기기 토큰·서비스 계정 키를 로그에 남기지 않는다. 토큰은 앞뒤 일부만.
- 예외 로그가 SQL 전문·파일 경로를 사용자 응답으로 나가게 하지 않는다. 응답에는 `request_id`만.

## Rule (진단에 필요한 최소 기록)
- 부팅 시 1회: 앱 버전(커밋 해시), 설정 요약(비밀값 제외), 라디오 파라미터, DB 경로, 마이그레이션 리비전.
- 주기적 1줄: 프레임 수신 성공/CRC실패/파싱실패/중복 카운터, 마지막 수신 경과 시간.
- 무선 경로는 재현이 어렵다 — 파싱 실패 프레임의 원본 hex를 반드시 남긴다.

## Anti-pattern
- `print()` 사용
- f-string으로 미리 포맷한 로그 메시지
- 값이 문장에 녹아 grep 불가 (`f"device {id} sent {n} frames"`)
- `logger.error(str(e))` (스택 소실)
- 파일 핸들러로 직접 로그 파일 기록
- journald 보존 상한 미설정
- 프레임마다 INFO 로그
- 동일 오류 반복 로그 억제 없음
- 토큰·키 전체 로깅
- 부팅 로그에 버전·설정 요약 없음 (배포된 게 뭔지 확인 불가)
