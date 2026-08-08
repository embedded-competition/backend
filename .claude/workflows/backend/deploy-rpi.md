---
name: backend-deploy-rpi
description: 검증된 변경분을 Raspberry Pi에 배포하거나 배포 실패를 롤백할 때 따르는 절차. systemd + uv 단일 호스트 기준.
---
## 적용 시점
- main에 머지된 변경을 Pi에 반영할 때.
- 마이그레이션이 포함된 변경을 반영할 때 (백업 단계가 필수라 더 중요).
- 배포 후 이상이 확인돼 되돌릴 때.

## 사전 조건
- 변경분이 main에 머지됨. 검증되지 않은 브랜치를 Pi에 올리지 않는다.
- CI green (`ruff`·`mypy`·`pytest`).
- Pi에 SSH 접근 가능. `deploy/` 자산이 repo에 있음.

## 절차

### 1. 배포 전 상태 기록
- 현재 커밋 해시와 Alembic 리비전을 기록한다. 롤백 목표점이다.
- `systemctl status`로 현재 서비스 정상 여부 확인. 이미 죽어 있으면 배포가 원인이 아님을 먼저 구분한다.
- 디스크 여유 확인. DB 백업 + batch 마이그레이션은 공간을 쓴다.

### 2. 코드 동기화
- `git fetch && git checkout <target-commit>`. 태그 또는 커밋 해시로 고정한다.
- `uv sync --frozen`. lock 불일치로 실패하면 여기서 멈춘다 — 강제로 넘기지 않는다.

### 3. DB 백업 (마이그레이션 유무와 무관하게 수행)
- 서비스 중지 후 DB 파일 + WAL 파일을 타임스탬프 붙여 복사한다.
- 백업 파일 크기가 0이 아닌지 확인한다. 확인 없는 백업은 백업이 아니다.

### 4. 마이그레이션
- `alembic current`로 현재 리비전 확인 → `alembic upgrade head`.
- 실패 시 즉시 중단하고 6번(롤백)으로 간다. 부분 적용 상태로 서비스를 올리지 않는다.
- batch 모드 리비전이 포함되면 테이블 복사가 일어난다. 소요 시간과 디스크를 미리 확인한다.

### 5. 기동 및 확인
- `systemctl restart <service>` → `systemctl status`로 active 확인.
- `/health` 호출해 `process`·`database`·`lora_radio`·`push` 각각 확인. 200이면 끝이 아니라 구성요소별 상태를 본다.
- `journalctl -u <service> -n 50`으로 부팅 로그 확인 — 앱 버전, 라디오 초기화 결과, 마이그레이션 리비전.
- 실제 프레임 수신을 1건 이상 확인한다. 서비스가 떠 있는 것과 수신되는 것은 다르다.
- `ps -o rss=`로 실제 메모리 사용량을 기록한다.

### 6. 롤백
- 트리거: 마이그레이션 실패, 기동 실패, `/health` 구성요소 실패, 프레임 수신 0.
- 절차: 서비스 중지 → 이전 커밋 checkout → `uv sync --frozen` → 3번 백업 파일로 DB 복원 → 서비스 시작 → `/health` 확인.
- `alembic downgrade`를 롤백 정본으로 쓰지 않는다. 백업 복원이 정본이다.

### 7. 기록
- 배포한 커밋·리비전·측정 RSS·확인 결과를 커밋 또는 이슈에 남긴다.
- 문제가 있었으면 원인과 조치를 남긴다. 같은 배포 실수를 두 번 하지 않기 위한 유일한 장치다.

## 금지
- 검증 안 된 브랜치를 Pi에 직접 배포
- DB 백업 없이 마이그레이션 실행
- `uv sync` (lock 무시)
- `/health` 확인 없이 배포 완료 선언
- Pi에서 직접 소스 편집 후 그대로 운영 (다음 배포에 덮임)
- 마이그레이션 부분 실패 상태로 서비스 기동
- 앱 startup에서 자동 `alembic upgrade head`

## 인용 관계
- 배포 자산·unit 파일: `conventions/backend/deploy/systemd-rpi.md`
- 마이그레이션 작성: `conventions/backend/framework/alembic.md`, `workflows/backend/migration.md`
- 헬스체크 정의: `conventions/backend/observability/observability.md`
- 로그 확인: `conventions/backend/observability/logging.md`
