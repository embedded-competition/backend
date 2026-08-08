---
name: backend-deploy-systemd-rpi
description: Raspberry Pi Zero 2W에 systemd + uv로 서비스를 배포·재시작·롤백하거나 unit 파일·자원 제한·장치 권한을 다룰 때 적용.
---
## Rule (배포 자산은 커밋된다)
- systemd unit 파일·배포 스크립트·`.env.example`은 `deploy/` 아래 커밋한다. Pi에 손으로 만든 파일이 SSOT가 되면 재구축이 불가능해진다.
- 배포 절차는 `deploy/deploy.sh` 한 스크립트로. 문서에만 적힌 수동 명령 나열 금지.
- Pi에서 직접 편집한 설정은 다음 배포에 덮인다는 전제로 운영한다. 임시 수정은 커밋으로 되돌린다.

## Rule (unit 파일)
- `Type=simple`, `ExecStart=/home/<user>/.local/bin/uv run --frozen uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1`.
- `WorkingDirectory`를 repo 경로로 고정. 상대 경로 의존 제거.
- `Restart=always` + `RestartSec=5`. 크래시 시 자동 복구.
- `EnvironmentFile=`로 `.env` 주입. unit 파일에 비밀값 직접 기재 금지.
- `After=network-online.target` + `Wants=network-online.target`. FCM 발송에 네트워크가 필요하다.
- `StandardOutput=journal`. 파일 로그 직접 쓰지 않는다(SD카드 수명).

## Rule (자원 제한 — 512MB)
- `MemoryMax=`를 실측 RSS의 2배 수준으로 설정한다. 누수 시 OOM killer가 시스템 전체 대신 이 서비스만 잡게 한다.
- 스왑은 끄거나 최소화한다. Pi Zero 2W에서 SD카드 스왑은 성능 붕괴 + 카드 수명 소모다.
- 배포 후 `systemctl status` + `ps -o rss=`로 실제 RSS를 확인해 기록한다. 추정치로 넘기지 않는다.

## Rule (장치 권한)
- SPI·GPIO 접근은 서비스 실행 사용자를 `spi`·`gpio` 그룹에 넣어 해결한다. `root`로 실행하지 않는다.
- `User=`를 전용 계정으로 지정한다. `pi` 계정 그대로 쓰지 않는다.
- `/boot/firmware/config.txt`의 `dtparam=spi=on` 활성화 상태를 배포 스크립트가 확인한다.

## Rule (배포 순서)
- ① `git pull` → ② `uv sync --frozen` → ③ **DB 파일 백업 복사** → ④ `alembic upgrade head` → ⑤ `systemctl restart` → ⑥ `/health` 확인.
- `--frozen` 없이 동기화하지 않는다. lock 무시는 Pi에서 다른 버전이 깔리는 경로다.
- Pi에서 소스 빌드가 필요한 패키지(휠 없는 ARM 패키지)는 도입 전에 확인한다. Pi Zero 2W 컴파일은 수십 분 단위다.
- 롤백은 이전 커밋 checkout + DB 백업 복원. 배포 전 백업이 없으면 롤백이 불가능하다.

## Rule (헬스체크)
- `/health`는 프로세스 생존 + DB 연결 + LoRa 라디오 상태를 구분해 반환한다. 하나로 뭉치지 않는다.
- 라디오 상태는 마지막 프레임 수신 경과 시간으로 판단한다. 무선 두절이 200 OK로 보이면 안 된다.

## Anti-pattern
- unit 파일을 Pi에만 만들고 repo에 커밋 안 함
- `ExecStart`에 `python` 직접 호출 (`uv run --frozen` 사용)
- unit 파일에 API 키·토큰 평문
- `User=root`로 실행
- `MemoryMax` 미설정
- 파일 경로에 애플리케이션 로그 직접 기록 (journald 사용)
- `uv sync` (lock 무시)
- 마이그레이션 전 DB 백업 생략
- 배포 후 `/health` 미확인
- `/health`가 DB·라디오 상태를 구분 없이 200으로 반환
- 스왑 켠 채 운영
