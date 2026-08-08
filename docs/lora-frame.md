# LoRa 프레임 포맷 v1

**노드 펌웨어(C)와 서버(Python)가 공유하는 계약이다.** 한쪽만 바꾸면 조용히 깨진다.
이 문서가 SSOT — 노드 코드와 `app/infrastructure/lora/frame.py`가 여기에 맞춘다.

관련: [db-schema.md](db-schema.md) · [api-contract-reconciliation.md](api-contract-reconciliation.md)

## 전제

| 항목 | 값 | 근거 |
|---|---|---|
| 판정 위치 | **노드** | 상태기계·signature 계산이 노드에 있다. 서버는 기록·디스패치만 |
| raw 전송 | 안 함 | 대역폭. 튜닝 raw는 USB 시리얼 로거 경로 |
| 전송 트리거 | 상태 전이 즉시 + heartbeat(기본 5분) | duty cycle 예산 |
| 엔디안 | **리틀엔디안** (`<`) | ESP32·ARM 양쪽 네이티브 |
| 좌표 | 상태 전이 프레임에만 포함 | 주차 중엔 안 움직인다. heartbeat 8B 절약 |

## 레이아웃

기본 43바이트, GPS 포함 시 51바이트.

| offset | size | 필드 | 타입 | 인코딩 |
|---|---|---|---|---|
| 0 | 1 | `version` | uint8 | 이 문서 = `1` |
| 1 | 1 | `flags` | uint8 | 아래 비트표 |
| 2 | 6 | `device_id` | bytes | MAC 6바이트 그대로 |
| 8 | 2 | `seq` | uint16 | 노드가 증가. 랩어라운드 허용 |
| 10 | 4 | `measured_at` | uint32 | epoch 초 (UTC) |
| 14 | 1 | `state` | uint8 | 0=WARMUP 1=NORMAL 2=WATCH 3=ALARM 4=FAULT |
| 15 | 2 | `batt_mv` | uint16 | mV 그대로 |
| 17 | 2 | `voc_dev` | int16 | ×100 |
| 19 | 2 | `voc_slope` | int16 | ×100 |
| 21 | 2 | `h2_dev` | int16 | ×100 |
| 23 | 2 | `h2_slope` | int16 | ×100 |
| 25 | 2 | `co_dev` | int16 | ×100 |
| 27 | 2 | `co_slope` | int16 | ×100 |
| 29 | 2 | `temp_c` | int16 | ×100 |
| 31 | 2 | `humidity_pct` | int16 | ×100 |
| 33 | 2 | `d_rh_dt` | int16 | ×100 |
| 35 | 2 | `pressure_dev` | int16 | ×100 |
| 37 | 2 | `pressure_rate` | int16 | ×100 |
| 39 | 2 | `sig_hold_s` | uint16 | 초 |
| 41 | 8 | `lat`, `lon` | float32 ×2 | **`flags.has_gps`일 때만 존재** |
| 41 또는 49 | 2 | `crc` | uint16 | CRC-16/CCITT-FALSE |

### flags 비트

| 비트 | 의미 |
|---|---|
| 0 | `has_gps` — 좌표 8바이트가 뒤따른다 |
| 1 | `latched` — ALARM latch 유지 중 |
| 2 | `sig_rise` — 급변 |
| 3 | `sig_hold` — 지속 |
| 4 | `sig_no_recover` — 무회복 |
| 5 | `water` — 침수·누액 감지 |
| 6 | `has_signature` — signature 3요소가 유효하다 |
| 7 | 예약 |

`has_signature`가 0이면 비트 2~4를 읽지 않는다. "전부 false"와 "안 보냄"을 구분해야
오경보 분석에서 근거 부재를 오해하지 않는다.

### 결측값

int16 필드는 **`-32768`(INT16_MIN)이 "값 없음"**이다. 센서 미장착·측정 실패를 0으로
채우면 "정상 판독 0"과 구분되지 않는다.

### CRC

- 알고리즘: CRC-16/CCITT-FALSE (poly `0x1021`, init `0xFFFF`, no reflect, xorout `0x0000`)
- 범위: `version`부터 CRC 직전까지 (CRC 자신 제외)

## 크기 검토

`api-contract-reconciliation.md` §C1에서 지적한 대로 앱 문서의 "14B"로는 불가능하다.

| 구성 | 바이트 |
|---|---|
| heartbeat (GPS 없음) | 43 |
| 상태 전이 (GPS 포함) | 51 |

SF7/BW125 기준 43B 프레임의 on-air time은 대략 100ms 수준이다. 5분 주기면 duty
cycle 점유가 0.04% 미만이라 규제 여유가 크다. ALARM 시 고빈도 전환(예: 10초 주기)에도
0.6% 수준으로 1% 제한 안에 들어온다.

**1초 주기는 불가능하다** — 앱의 폴링 주기 가정(§B3)이 이 계산과 맞지 않는다.

## 버전 관리

- 필드 추가·삭제·오프셋 변경·스케일 변경은 전부 `version` 증가를 요구한다
- 서버는 모르는 version을 만나면 파싱하지 않고 `unsupported_frame_version`으로 거절 로그를 남긴다
- 노드와 서버 배포 순서: **서버 먼저** (새 version을 이해하게 한 뒤 노드를 올린다)

## 참조 구현

- 서버 파서: `app/infrastructure/lora/frame.py`
- 노드 인코더: (펌웨어 repo — 작성 시 이 문서 링크할 것)

## 미확정

| 항목 | 상태 |
|---|---|
| GPS 모듈 BOM | 미확정. `has_gps=0`이면 서버는 좌표 없이 정상 처리한다 |
| CO 센서(MQ-7) | 미도입. `co_dev`·`co_slope`는 INT16_MIN으로 채운다 |
| 압력 센서 | 미도입. 동일 |
| 노드 RTC 정확도 | 서버가 `received_at`을 따로 기록해 편차를 관측한다 |
