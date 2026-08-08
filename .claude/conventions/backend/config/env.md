---
name: backend-config-env
description: 환경변수와 비밀값을 yml placeholder·.env·GitHub Secrets로 정의·주입·참조할 때 적용
---

## Rule
- 환경변수는 yml의 `${VAR}` placeholder로만 참조한다. 코드에서 `System.getenv()` 직접 호출 금지 (테스트 어려움).
- 환경변수 명명은 `SCREAMING_SNAKE_CASE`. 도메인/관심사 prefix (`DB_*`, `PYTHON_*`, `VISION_*`).
- local 개발용 기본값은 `application-local.yml`의 placeholder default(`${DB_PASSWORD:dev}`)로 제공.
- prod 비밀값은 **GitHub Secrets**만 사용 
- 로컬 `.env` 파일은 git에서 제외 (`.gitignore`). `.env.example`만 commit해 키 목록 공유.
- 새 환경변수 추가 시 `.env.example` 동시 갱신 + base yml에 placeholder 추가.
- secrets 로딩은 컨테이너 시작 시점 한 번. 런타임 변경 금지.

## Anti-pattern
- 코드에서 환경변수 직접 읽기 (`System.getenv`/`@Value` 외 — yml placeholder 경유)
- 비밀값을 git에 commit (`.env`, credentials.json 등)
- prod secrets를 로컬 yml/`.env`에 적기
- 환경변수에 비밀값 prefix(`SECRET_`, `PASSWORD_`) 없이 모호하게 이름 짓기
- 같은 의미 변수 여러 이름(`DB_PWD`/`DB_PASSWORD`)
- 환경변수 default를 prod에 활성화 (placeholder default는 local 한정)
- Docker 이미지 안에 secret bake (런타임 주입만)
- secrets를 로그에 출력 (마스킹 필수)
