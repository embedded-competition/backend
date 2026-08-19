# 배포 설계

대상: 전동 킥보드 배터리 화재 조기감지 백엔드. GitHub Actions로 Raspberry Pi Zero 2W에 배포.
스키마 변경 절차는 [db-schema.md](db-schema.md). 앱 계약은 [api-contract-reconciliation.md](api-contract-reconciliation.md).
Pi 최초 셋업 명령은 [cloudflare-setup.md](cloudflare-setup.md), 장소를 옮겼을 때의 복구는
[pi-recovery.md](pi-recovery.md). 이 문서는 **왜 그렇게 하는지**만 적는다.

## 설계 전제

| 항목 | 값 | 근거 |
|---|---|---|
| 배포 대상 | Raspberry Pi Zero 2W 1대 (512MB) | 아래 D1 |
| 로컬 접속 | `ssh user@pi.local` | 계정 `user`, 호스트네임 `pi` |
| 실행 계정 | `user` (로그인 계정과 동일) | 아래 D10 |
| OS | Raspberry Pi OS **64비트** | 아래 D7 |
| 실행 | systemd + uv + uvicorn `--factory` | `deploy/orca-backend.service` |
| 저장소 | SQLite 파일 (SD카드) | 단일 writer + 다중 reader |
| 네트워크 | NAT 뒤. 고정 IP·포트포워딩 권한 없음 | 대회 현장·기숙사 망 가정 |
| 인그레스 | Cloudflare Tunnel (보유 도메인 서브도메인) | 아래 D2 |
| 배포 트리거 | semver 태그 push | 아래 D4 |
| 배포 경로 | Actions → SSH over Cloudflare Access | 아래 D3 |
| 스테이징 | 없음. 상시 가동 시뮬레이터가 대체 | 아래 D8 |
| 비밀 | Pi의 `.env` (systemd `EnvironmentFile`). Actions는 안 만짐 | 아래 D6 |

## 전체 흐름

```
PR ──────────────► ci.yml (기존)
                   make check · openapi drift · --no-dev boot
                        │ 통과해야 머지 가능
main 머지 ────────► 배포 없음
                        │
v0.1.0 태그 push ─► deploy.yml
                   ① ci 재실행 (태그 커밋 기준)
                   ② cloudflared access ssh → Pi
                   ③ deploy/deploy.sh v0.1.0
                        fetch · checkout --detach
                        uv sync --frozen --extra pi
                        DB 백업 (.db/-wal/-shm, 비었으면 중단)
                        alembic upgrade head
                        systemctl restart
                        localhost /health
                   ④ 공개 호스트네임 /health          ← 터널까지 검증
                   ⑤ 실패 시 이전 태그로 자동 롤백 + DB 복원
```

## 핵심 결정

### D1. 백엔드는 클라우드로 가지 않는다

`app/infrastructure/lora/spi.py`가 SX1276을 SPI로 읽고 `gpio.py`가 GPIO로 리셋을 건다.
systemd unit도 `SupplementaryGroups=spi gpio`를 요구한다. 수신기가 곧 서버라서 프로세스는
무선 하드웨어와 같은 보드에 있어야 한다.

"Pi는 게이트웨이만 하고 API는 클라우드" 안은 D9에 미도입 사유와 함께 적는다.

### D2. 인그레스는 Cloudflare Tunnel

Pi는 NAT 뒤에 있고 공유기 관리 권한을 전제할 수 없다. 아웃바운드 터널만이 성립한다.

| 방식 | 도메인 | 고정 URL | 무료 한도 | 엣지 WAF | Pi 메모리 |
|---|---|---|---|---|---|
| **Cloudflare Tunnel** | 필요 | O | 사실상 무제한 | **O** | ~30MB |
| Tailscale Funnel | 불필요 | O (`*.ts.net`) | fair use | X | ~30MB |
| ngrok | 불필요 | O (고정 1개) | **월 1GB** + 브라우저 경고 | X | ~25MB |
| 포트포워딩 + DDNS | 필요 | O | — | X | 0 |
| Quick Tunnel / localtunnel | 불필요 | **X** | — | X | — |

포트포워딩은 관리 권한 전제 불가로 탈락. ngrok은 월 1GB가 폴링 트래픽에 부족하고 초과 시
시연이 죽는다. 고정 URL이 없는 것들은 앱에 주소가 박히므로 탈락.

**Tailscale Funnel과 실제로 경합했고 도메인 보유 여부가 갈랐다.** Funnel의 유일한 우위는
도메인이 필요 없다는 점인데, Cloudflare Registrar에 이미 도메인이 있어 그 우위가 성립하지
않는다. 반대로 Cloudflare는 엣지 WAF·레이트리밋을 주고, 그게 D5의 완화 수단이 된다.

Funnel은 공개 클라이언트 대상이라 P2P 상쇄가 없어 트래픽 100%가 Tailscale 서버를 지나고
대역폭이 fair use다. Cloudflare는 기존 엣지에 얹는 구조라 한계비용이 사실상 0이다.

동작 원리: 공개 DNS가 Cloudflare 엣지를 가리키고 Pi는 아웃바운드 연결만 유지한다.
Pi의 IP는 어디에도 기록되지 않으므로 **와이파이·네트워크가 바뀌어도 공개 주소가 유지된다.**

TLS는 Cloudflare 엣지에서 종료되고 터널 구간에서 재암호화된다. 즉 **Cloudflare는 평문을
볼 수 있다.** WAF·레이트리밋이 가능한 이유가 그것이고, 그 신뢰를 지불한 대가다.
(Tailscale Funnel은 SNI만 보고 전달해 평문을 못 보는 대신 WAF도 못 한다.)

메모리 예산: 백엔드 `MemoryMax=220M` + cloudflared ~30MB + OS ~120MB ≈ 370MB / 512MB.

**호스트네임은 나중에 바꿔도 싸다.** 프로젝트 이름이 확정되지 않아 기존 보유 도메인의
서브도메인을 임시로 쓴다. 하나의 터널이 여러 호스트네임을 동시에 서비스할 수 있으므로,
확정 후에는 `config.yml`에 ingress 한 줄과 DNS 라우트 하나를 추가해 **둘을 병행 운영하다가**
앱 배포가 끝나면 옛 이름을 지우면 된다. Pi 재설정도 무중단 전환도 필요 없다.

이 성질 때문에 임시 이름 선정에 시간을 쓰지 않는다.

### D3. 배포 경로는 Actions → SSH over Cloudflare Access

Pi가 NAT 뒤라 GitHub 호스티드 러너가 직접 닿지 못한다.

| | 인바운드 | Pi 메모리 | 비밀 | Actions가 결과를 보나 |
|---|---|---|---|---|
| Pi에 self-hosted runner | 불필요 | **+150~200MB** | Pi에 GitHub 토큰 | 봄 |
| **Actions → SSH over CF Access** | 불필요 | +0 | GH Secrets | 봄 |
| Pi가 릴리스 폴링 (systemd timer) | 불필요 | +0 | 없음 | **못 봄** |

self-hosted runner 탈락 근거: 512MB에서 러너 상주 + `uv sync` 동시 실행이면 백엔드가
OOM으로 재시작될 수 있다. 감지 시스템이 배포마다 죽는 것은 허용 불가.

채택안은 D2에서 이미 깔린 cloudflared에 SSH 라우트를 하나 더 여는 것이라 새 데몬이 없다.

호스트네임 2개를 한 터널에 태우고 **Access는 SSH 쪽에만 건다.**

| 호스트네임 | 대상 | Cloudflare Access |
|---|---|---|
| `api.agenthub.work` | `http://localhost:8000` | **걸면 안 됨** — 앱이 인증 못 함 |
| `ssh.agenthub.work` | `ssh://localhost:22` | **필수** — service token만 통과 |

API에 Access를 걸면 모바일 앱이 전부 막힌다. 가장 흔한 사고다.

필요한 GH Secrets — 값은 Pi 셋업 때 채운다.

| 이름 | 용도 |
|---|---|
| `CF_ACCESS_CLIENT_ID` | Cloudflare Access service token |
| `CF_ACCESS_CLIENT_SECRET` | 같음 |
| `DEPLOY_SSH_KEY` | Pi `user` 계정 배포 전용 키 (개인키) |
| `DEPLOY_KNOWN_HOSTS` | Pi의 SSH 호스트 키. 없으면 매 배포가 처음 보는 호스트를 그냥 믿는다 |
| `DEPLOY_HOST` | `ssh.agenthub.work` |
| `PUBLIC_HEALTH_URL` | `https://api.agenthub.work/health` |

Access 정책은 **Action을 `Service Auth`로** 만들어야 한다. `Allow`로 만들면 사람 로그인용이
되어 CI가 뚫지 못한다.

### D4. 배포 트리거는 semver 태그, main 머지가 아니다

main 머지마다 재시작하면 수신이 끊긴다. LoRa 프레임은 재전송되지만 그 사이의 상태 전이를
놓칠 수 있다. 화재 감지 시스템에서 배포 시점은 사람이 정한다.

`main`은 항상 배포 가능한 상태를 유지하고, 실제 반영은 태그가 결정한다.

### D5. `POST /devices`는 지금 공개 상태로 둔다 (미결정)

인증 없이 deviceToken을 발급하는 유일한 경로다. 터널로 노출되는 순간 누구나 기기를 등록하고
토큰을 받을 수 있다. 앱이 써야 하므로 Cloudflare Access로 앞단을 막을 수 없다.

**대회 기간 한정 운영으로 보고 지금은 방치한다.** 상시 운영으로 넘어가면 아래 중 하나를 붙인다.

| 완화안 | 서버 변경 | 앱 변경 | 비고 |
|---|---|---|---|
| CF 레이트리밋 (IP당 분당 N회) | 없음 | 없음 | **D2에서 Cloudflare를 고른 실질 이유.** 대시보드 설정만으로 끝난다 |
| 등록 시크릿 헤더 | `Settings` 1줄 + 의존성 | 필요 | 시크릿이 앱 바이너리에 박혀 추출 가능 |
| 등록 코드 사전 발급 | 테이블 1개 + 발급 경로 | 필요 | 가장 확실. 설치 절차가 늘어난다 |

**전환 조건**: 대회 종료 후에도 서비스를 유지하기로 결정하는 시점.

### D6. 설정은 Actions 시크릿이 SSOT다 (**개정** — 원안은 "Pi에만 둔다")

`.env`는 systemd `EnvironmentFile=/home/user/backend/.env`로 주입되고 저장소에 없다
(`.env.example`이 키 목록의 SSOT, `extra="forbid"`라 오타 나면 부팅 실패).

**원안**: Actions는 `.env`를 만들지도 읽지도 않는다. 배포 파이프라인이 뚫려도 앱 운영
비밀은 새지 않는다.

**개정 이유**: 그 대가를 v0.6.7에서 받았다. 저장소에서 `APP_FAKE_*` 두 키를 없앴는데
Pi의 `.env`에는 남아 있었고, `extra="forbid"`가 부팅을 막아 배포가 실패·롤백됐다.
코드와 설정이 따로 움직이면 이 사고는 키를 없앨 때마다 되풀이된다. 손으로 고치는 절차를
문서에 적는 것은 해결이 아니다 — 배포는 사람 기억이 아니라 명령 하나에 있어야 한다(D5).

**확정**: `prod` 환경 시크릿 `APP_ENV_FILE`이 `.env` 전문을 갖는다. 배포가 코드 동기화
직전에 Pi로 내려 쓰고, 롤백은 직전 `.env`(`data/backups/env.prev`)로 함께 되돌린다.
설정과 코드가 같은 태그에 묶인다.

**대가**: 파이프라인이 뚫리면 운영 비밀(관리실 번호, CORS origin 등)도 함께 샌다. 원안이
막으려던 것이 바로 이것이고, 그 위험을 알고 고른 트레이드오프다. Cloudflare Access 서비스
토큰과 `prod` 환경 보호 규칙이 유일한 방벽이다.

**함정**: 시크릿 내용이 `.env`를 통째로 덮는다. 잘린 내용을 붙여 넣으면 빠진 키가 조용히
기본값으로 떨어진다 — `APP_PUSH_DELIVERY`가 사라지면 푸시가 로그로만 간다. 배포는
`APP_ENVIRONMENT` 존재와 키 개수(≥10)만 확인한다. 값이 맞는지는 확인하지 못한다.

시크릿이 비어 있으면 Pi의 기존 `.env`를 그대로 쓴다. 이 결정을 되돌리는 데 코드 변경이
필요 없다.

`deploy.sh`는 서비스를 세우기 전에 `.env`를 새 코드로 한 번 읽고, 어긋나면 거기서 멈춘다.
돌고 있는 서비스를 내리지 않는다.

Pi `.env`에서 로컬과 달라야 하는 값:

```
APP_ENVIRONMENT=pi
APP_ENABLE_DOCS=false      # 터널 노출 상태. /docs·/openapi.json 닫는다
APP_LOG_FORMAT=json        # journald 파싱
APP_LORA_SOURCE=sx1276     # 실제 하드웨어
APP_PUSH_DELIVERY=expo     # 실제 발송
APP_MANAGEMENT_PHONE=...
```

`APP_ENABLE_DOCS=false`의 대가: 앱 팀이 Swagger를 못 본다. 저장소의 `docs/openapi.json`이
계약 SSOT이고 `make openapi`가 드리프트를 막는다.

### D7. Raspberry Pi OS는 64비트로 설치한다

32비트(armv7)면 `pydantic-core`가 aarch64 휠을 받지 못해 Rust 소스 빌드로 넘어간다.
Pi Zero 2W에서 수십 분이 걸리고 512MB로는 실패할 수 있다. Pi Zero 2W는 Cortex-A53이라
64비트를 지원한다.

`uv sync --frozen --extra pi`가 lock에 고정된 버전만 설치하므로, 휠이 있는 아키텍처를
고르는 것이 유일한 대비책이다.

### D8. 스테이징 환경을 두지 않는다

Pi가 1대뿐이고 두 번째를 두는 비용이 얻는 것보다 크다. 대신 두 층으로 대체한다.

| 층 | 수단 | 검증 범위 |
|---|---|---|
| CI | `make check` + contract + `--no-dev` boot | 코드·계약·의존성 |
| 로컬·운영 | 상시 가동 시뮬레이터 | 수신→저장→전이→디스패치 전 경로 |

시뮬레이터는 설정 없이 늘 떠 있고 무선 수신기와 나란히 돈다. 실제 바이트를 만들어 파서를
그대로 태우고, 노드가 하는 판정까지 흉내낸다. 운영에서도 켜져 있으므로 실기기 없이 앱
화면을 확인하는 일이 배포 후에도 가능하다. 흐름을 손으로 조절하는 방법은
[simulation.md](simulation.md)에 있다. 남는 위험은 하드웨어 경계(SPI·GPIO·전파)뿐이고,
그건 어떤 스테이징으로도 못 덮는다.

### D9. 롤백은 태그 되감기 + DB 파일 복원

마이그레이션은 forward-only(Expand-Contract)라 `alembic downgrade`를 배포 경로에서 쓰지 않는다.
스키마를 되돌리는 유일한 수단은 배포 직전 백업 파일이다.

`deploy.sh`가 이미 `.db`/`-wal`/`-shm` 3개를 타임스탬프로 복사하고 **비어 있으면 중단**한다.
현재는 롤백 절차가 종료 메시지의 안내문으로만 있다 — 이를 실패 시 자동 실행으로 바꾼다.

롤백 후 DB는 백업 시점으로 돌아가므로 **그 사이 수신한 프레임은 유실된다.** 배포 창을 짧게
가져가는 것이 유일한 완화책이다.

### D10. 서비스를 로그인 계정(`user`)으로 돌린다 (잠정)

전용 서비스 계정(`orca` 등)을 파지 않고 Pi 로그인 계정을 그대로 쓴다.

| | 전용 계정 | 로그인 계정 (채택) |
|---|---|---|
| 셋업 단계 | uv 재설치·`~/.local/bin` 경로·authorized_keys·clone 소유권 전부 재구성 | 없음 |
| 계정 탈취 시 | 서비스와 로그인이 분리 | **함께 뚫린다** |
| 이 규모에서 끊는 파급 | 없음 (Pi 1대, 단일 목적) | — |

지금은 계정 분리가 끊어 줄 파급이 실재하지 않는다. 반면 계정을 새로 파면 셋업 단계가 늘고
그만큼 틀릴 자리가 생긴다. `--system` 계정으로 만들면 로그인이 막혀 배포 SSH는 결국
로그인 계정으로 붙어 `sudo`로 실행하는 형태가 되므로 분리 이득의 절반이 사라진다.

**전환 조건**: 대회 종료 후에도 서비스를 유지하기로 결정하는 시점 (D5와 동일).
그때 `deploy/orca-backend.service`의 `User`/`Group`/경로 5줄과 배포 키 소유자를 함께 옮긴다.

## 구현 인벤토리

| 산출물 | 상태 |
|---|---|
| `deploy/deploy.sh` | 있음 — fetch·sync·백업·마이그레이션·재시작·헬스체크 |
| `deploy/orca-backend.service` | 있음 — `--factory`, `MemoryMax`, journald |
| `.github/workflows/ci.yml` | 있음 |
| `.github/workflows/deploy.yml` | 있음 — 태그 트리거, ci 재실행, 공개 경로 검증, 실패 시 롤백 |
| `deploy/rollback.sh` | 있음 — manifest 기반. deploy.sh와 Actions가 모두 부른다 |
| cloudflared unit 파일 | 만들지 않음 — `cloudflared service install`이 생성한다 |
| cloudflared `config.yml` | 저장소에 두지 않음 — UUID가 Pi마다 달라 [cloudflare-setup.md](cloudflare-setup.md)가 SSOT |

## Pi 사전 준비

한 번만 하면 된다.

### 1. 백엔드

```bash
ssh user@pi.local

# Raspberry Pi OS Lite에는 git이 없다. spidev는 aarch64 휠이 없어 소스 빌드로
# 넘어가므로 Python 헤더와 컴파일러가 필요하다.
sudo apt-get update && sudo apt-get install -y git python3-dev build-essential

sudo usermod -aG spi,gpio user                    # 재로그인해야 반영된다
curl -LsSf https://astral.sh/uv/install.sh | sh   # /home/user/.local/bin/uv

git clone https://github.com/embedded-competition/backend.git ~/backend
cd ~/backend
cp .env.example .env                              # 값 채우기 (D6)

mkdir -p data
uv run alembic upgrade head

sudo cp deploy/orca-backend.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now orca-backend
```

기동에 약 9초가 걸린다. 그 전에 헬스체크를 치면 연결 거부가 뜬다.

SX1276을 아직 안 붙였으면 `/dev/spidev*`가 없다. `raspi-config`로 SPI를 켜기 전에는
`APP_LORA_SOURCE=none`으로 둔다 — 배포 경로와 하드웨어를 분리해 검증한다(D8과 같은 이유).
시뮬레이터는 이 값과 무관하게 돌므로 그 상태로도 앱 화면 전체를 확인할 수 있다.

### 2. 터널·Access·배포 키

[cloudflare-setup.md](cloudflare-setup.md)에 명령 순서가 있다. 터널 이름은 `embedded`,
호스트네임은 `api.agenthub.work` / `ssh.agenthub.work`다.

## 첫 배포 후 실측할 것

| 항목 | 방법 | 조치 |
|---|---|---|
| RSS | `systemctl show -p MainPID` → `ps -o rss=` | `MemoryMax=220M`을 실측 2배로 조정 |
| `uv sync` 소요 | 배포 로그 | 5분 초과면 휠 캐시 검토 |
| SD 쓰기량 | `iostat` 또는 journald 크기 | 과하면 uvicorn `--no-access-log` |
| 터널 지연 | 앱에서 `/telemetry/latest` 왕복 | 폴링 주기 재검토 |

`MemoryMax=220M`은 아직 추측값이다. unit 파일 주석도 실측 후 조정을 요구한다.

## 미도입 (지금 안 넣는 것과 이유)

| | 이유 | 도입 조건 |
|---|---|---|
| Docker | 512MB에서 런타임 오버헤드. `uv sync --frozen`이 이미 재현성을 준다 | Pi가 여러 대가 되어 이미지 배포가 이득일 때 |
| Pi=게이트웨이 + API=클라우드 | 수신 버퍼링·이중 배포 대상·대규모 리팩터링. 지금 얻을 게 없다 | 설치 지점이 여러 곳으로 늘어날 때 |
| 블루/그린·무중단 | 노드 1개 + 프로세스 1개. 재시작 수 초를 감수한다 | LoRa 프레임 유실이 실측으로 문제될 때 |
| 자동 릴리스 노트 | 태그 본문으로 충분 | 배포 빈도가 주 단위를 넘을 때 |
| 헬스체크 기반 자동 롤백 이상의 모니터링 | 관측 대상이 Pi 1대 | 상시 운영 전환 시 |
| 로그 원격 수집 | journald + `LOG_FORMAT=json`으로 로컬 조회 가능 | 현장 접근이 어려워질 때 |
