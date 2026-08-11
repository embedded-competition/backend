# LoRa 프레임 포맷 v2

**노드 펌웨어(C)와 서버(Python)가 공유하는 계약이다.** 한쪽만 바꾸면 조용히 깨진다.
이 문서가 SSOT — 노드 코드와 `app/infrastructure/lora/frame.py`가 여기에 맞춘다.

관련: [db-schema.md](db-schema.md) · [api-contract-reconciliation.md](api-contract-reconciliation.md)

## v1에서 바뀐 이유

v1은 노드 하드웨어가 확정되기 전에 썼다. 실제 노드(ESP32-C3 + MQ7·MQ8·SGP40·FSR402·수위)를
보고 나니 **채울 수 없는 필드**가 있었다.

| v1 필드 | 문제 | v2 처리 |
|---|---|---|
| `measured_at` (epoch) | 노드에 RTC도 시각 동기화도 없다 | `uptime_s`로 교체. 시각은 서버가 수신 시각으로 찍는다 |
| `temp_c`·`humidity_pct`·`d_rh_dt` | 온습도 센서 미장착 | **선택 블록**으로 분리. 없으면 6바이트가 아예 안 실린다 |
| `batt_mv` | 배터리 모니터 없음 | 선택 블록 |
| `pressure_rate` | 노드가 변화율을 안 구한다 | 선택 블록 |
| `*_dev` "z-score" | 노드는 표준편차를 추적하지 않는다. 구할 수 있는 건 기준선 대비 **비율**이다 | 정의를 상대 편차로 바꾼다 (아래) |

시각 필드 하나만으로도 버전을 올려야 했다. 올리는 김에 못 채우는 필드를 선택 블록으로
내려 평상시 프레임을 34바이트로 줄였다.

## 전제

| 항목 | 값 | 근거 |
|---|---|---|
| 판정 위치 | **노드** | 상태기계·기준선이 노드에 있다. 서버는 기록·디스패치만 |
| raw 전송 | 안 함 | 대역폭. 튜닝 raw는 USB 시리얼 로거 경로 |
| 전송 트리거 | 상태 전이 즉시 + heartbeat(권장 60초) | 아래 §전송 주기 |
| 엔디안 | **리틀엔디안** | ESP32·ARM 양쪽 네이티브 |
| 전송 인코딩 | **base64url(패딩 없음)** | 아래 §왜 base64인가 |
| 시각 | **서버가 찍는다** | 노드에 시계가 없다 |

## 레이아웃

### 고정부 — 32바이트

| offset | size | 필드 | 타입 | 인코딩 |
|---|---|---|---|---|
| 0 | 1 | `version` | uint8 | 이 문서 = `2` |
| 1 | 1 | `flags` | uint8 | 아래 비트표 |
| 2 | 1 | `present` | uint8 | 선택 블록 비트맵 |
| 3 | 6 | `device_id` | bytes | MAC 6바이트 그대로 |
| 9 | 2 | `seq` | uint16 | 노드가 증가. 랩어라운드 허용 |
| 11 | 4 | `uptime_s` | uint32 | 부팅 후 경과 초 |
| 15 | 1 | `state` | uint8 | 0=WARMUP 1=NORMAL 2=WATCH 3=ALARM 4=FAULT |
| 16 | 2 | `voc_dev` | int16 | ×100 |
| 18 | 2 | `voc_slope` | int16 | ×100 (/분) |
| 20 | 2 | `h2_dev` | int16 | ×100 |
| 22 | 2 | `h2_slope` | int16 | ×100 (/분) |
| 24 | 2 | `co_dev` | int16 | ×100 |
| 26 | 2 | `co_slope` | int16 | ×100 (/분) |
| 28 | 2 | `pressure_dev` | int16 | ×100 |
| 30 | 2 | `sig_hold_s` | uint16 | 초 |

### 선택 블록 — `present` 비트 순서대로 이어 붙인다

| 비트 | 블록 | size | 내용 |
|---|---|---|---|
| 0 | `env` | 6 | `temp_c` int16 ×100, `humidity_pct` int16 ×100, `d_rh_dt` int16 ×100 |
| 1 | `gps` | 8 | `lat` float32, `lon` float32 |
| 2 | `power` | 2 | `batt_mv` uint16 |
| 3 | `pressure_rate` | 2 | int16 ×100 |
| 4~7 | 예약 | — | 0으로 둔다 |

**블록은 비트 번호가 작은 것부터 순서대로 붙인다.** `present=0b0101`이면 `env`(6B) 다음에
`power`(2B)가 온다.

### 끝 — CRC 2바이트

| size | 필드 | 타입 |
|---|---|---|
| 2 | `crc` | uint16 |

- 알고리즘: CRC-16/CCITT-FALSE (poly `0x1021`, init `0xFFFF`, no reflect, xorout `0x0000`)
- 범위: `version`부터 CRC 직전까지 (CRC 자신 제외)

### 크기

| 구성 | 바이트 | base64url 문자 |
|---|---|---|
| **현재 노드** (선택 블록 없음) | **34** | **46** |
| + env | 40 | 54 |
| + env + gps + power | 50 | 68 |

## flags 비트

| 비트 | 의미 |
|---|---|
| 0 | `latched` — ALARM latch 유지 중 |
| 1 | `sig_rise` — 급변 |
| 2 | `sig_hold` — 지속 |
| 3 | `sig_no_recover` — 무회복 |
| 4 | `water` — 침수·누액 감지 |
| 5 | `has_signature` — signature 3요소(비트 1~3)가 유효하다 |
| 6 | `time_is_epoch` — `uptime_s`가 부팅 경과가 아니라 UTC epoch 초다 |
| 7 | 예약 |

`has_signature`가 0이면 비트 1~3을 읽지 않는다. "전부 false"와 "안 보냄"을 구분해야
오경보 분석에서 근거 부재를 오해하지 않는다.

`time_is_epoch`는 지금 노드에서 항상 0이다. 나중에 RTC나 시각 동기화가 붙으면 1로 올리고,
그때부터 서버가 노드 시각을 신뢰한다. 필드를 미리 열어 두어 그 전환에 버전 증가가 필요 없게 했다.

## `*_dev`의 정의 — 여기가 v1과 가장 다르다

**`dev = (현재값 / 기준선) − 1`** 을 ×100 한 int16이다.

| 상황 | `dev` 값 | 앱 표시 |
|---|---|---|
| 평소와 같음 | `0` | "평소와 같음" |
| 평소의 1.5배 | `50` | "평소의 1.5배" |
| 평소의 8배 | `700` | "평소의 8배" |

앱은 `배수 = dev / 100 + 1`로 환산한다. 차트의 "이 킥보드의 평소 수준" 점선이 정확히
`dev = 0`이다.

v1은 z-score라고 적었지만 **노드는 표준편차를 추적하지 않는다.** 3분 절사평균 기준선과
현재값의 비율이 노드가 실제로 가진 값이고, 앱 화면의 문구도 배수다. 있지도 않은 통계량을
계약에 적어 두면 펌웨어가 그것을 지어내야 한다.

### SGP40은 부호를 뒤집는다

MQ7·MQ8·FSR402는 값이 **올라갈 때** 위험이고, SGP40 raw는 VOC가 늘면 **내려간다**.

그대로 보내면 가스 채널마다 위험 방향이 달라져서, 서버와 앱이 채널별로 분기해야 한다.
**노드가 SGP40만 역수로 계산한다.**

```c
/* MQ7, MQ8, FSR402 */
dev = (current / baseline) - 1.0f;

/* SGP40 — 하락이 위험이므로 역수 */
dev = (baseline / current) - 1.0f;
```

이러면 **세 채널 모두 "양수 = 가스 증가 = 위험"** 이 되고 그 규칙이 서버·앱 전체에서 한 번만 적용된다.

## `*_slope`

**분당 `dev` 변화량**이다. 앱의 "평소의 8배 **속도로** 늘어남" 문구가 이 값을 쓴다.

```c
slope = (dev_now - dev_60s_ago) / 1.0f;   /* 1분당 */
```

노드가 이미 초당 샘플을 들고 있으므로 60샘플 전 값과 비교하면 된다. 구하지 못하는 동안에는
`INT16_MIN`을 넣는다.

## 결측값

int16 필드는 **`-32768`(INT16_MIN)이 "값 없음"**이다. 센서 미장착·측정 실패를 0으로 채우면
"정상 판독 0"과 구분되지 않는다. **`dev = 0`은 "평소와 같음"이라는 정상 판독이다.**

선택 블록 자체를 안 보내는 것과 블록 안에서 INT16_MIN을 보내는 것은 다르다. 전자는
"이 노드에 그 센서가 없다", 후자는 "센서는 있는데 이번 측정이 실패했다"이다.

## state 매핑

노드 내부 상태를 프레임의 `state`로 옮기는 표다.

| 노드 내부 | 프레임 `state` | 근거 |
|---|---|---|
| 기준선 미완성 | `0` WARMUP | 판정 불가 |
| 정상 | `1` NORMAL | |
| danger 감지, hold 미달 | `2` WATCH | 아직 확정 아님 |
| danger가 `DANGER_HOLD_SAMPLES` 이상 지속 | `3` ALARM | latch 대상 |
| ADC 포화 등 센서 이상 | `4` FAULT | **값이 아니라 센서를 못 믿는 상태** |

FAULT를 NORMAL로 접지 마라. 포화된 센서는 "정상"이 아니라 "모름"이다.

## 전송 주기

| 상황 | 주기 |
|---|---|
| 평상시 heartbeat | **60초** |
| 상태 전이 발생 | 즉시 1회 |
| ALARM 유지 중 | 10초 |

현재 펌웨어의 1초 주기는 SF9 기준 듀티 사이클이 30%를 넘어 규제·충돌 양쪽에서 성립하지
않는다. 60초면 0.5% 수준이다.

**판정은 계속 1초마다 하고 보고만 60초로 한다.** 노드가 이미 초당 샘플링·기준선 추적·
danger 판정을 하고 있으므로, 상태 전이 즉시 전송 경로만 있으면 감지 지연이 생기지 않는다.

## 왜 base64인가

RYLR은 `AT+SEND=<주소>,<길이>,<데이터>`의 줄 단위 텍스트 인터페이스다. 데이터에 `0x0A`·`0x0D`가
섞이면 AT 프레이밍이 깨지므로 **바이너리를 그대로 못 싣는다.** 인코딩이 필수다.

| 인코딩 | 34바이트 → | SF9 전파 시간 |
|---|---|---|
| hex | 68자 | 약 427 ms |
| **base64url** | **46자** | **약 325 ms** |

hex는 2배로 부풀어 CSV(78자, 468ms)와 별 차이가 없어진다. base64는 4/3배라 바이너리를
고른 이유가 실제로 남는다.

- **base64url** (`-`·`_` 사용, `+`·`/` 없음) — RYLR AT 파서와 충돌할 문자를 피한다
- **패딩(`=`) 없음** — 길이는 프레임 자체가 안다
- ESP-IDF는 `mbedtls_base64_encode`를 이미 포함한다

## 버전 관리

- 필드 추가·삭제·오프셋 변경·스케일 변경은 전부 `version` 증가를 요구한다
- **선택 블록 추가는 예외** — `present` 비트를 늘리는 것은 버전을 올리지 않는다. 모르는
  비트를 만나면 서버는 그 블록을 건너뛸 수 없으므로, **새 블록은 항상 마지막 비트에 붙인다**
- 서버는 모르는 version을 만나면 파싱하지 않고 `unsupported_frame_version`으로 거절한다
- 배포 순서: **서버 먼저** (새 version을 이해하게 한 뒤 노드를 올린다)

## 노드 참조 구현

```c
#include "mbedtls/base64.h"

#define FRAME_VERSION      2
#define INT16_MISSING      INT16_MIN

#define FLAG_LATCHED       (1u << 0)
#define FLAG_SIG_RISE      (1u << 1)
#define FLAG_SIG_HOLD      (1u << 2)
#define FLAG_SIG_NO_RECOV  (1u << 3)
#define FLAG_WATER         (1u << 4)
#define FLAG_HAS_SIGNATURE (1u << 5)
#define FLAG_TIME_IS_EPOCH (1u << 6)

static uint16_t crc16_ccitt_false(const uint8_t *data, size_t len)
{
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < len; ++i) {
        crc ^= (uint16_t)data[i] << 8;
        for (int bit = 0; bit < 8; ++bit) {
            crc = (crc & 0x8000) ? (uint16_t)((crc << 1) ^ 0x1021) : (uint16_t)(crc << 1);
        }
    }
    return crc;
}

static void put_u16(uint8_t *p, uint16_t v) { p[0] = v & 0xFF; p[1] = v >> 8; }
static void put_i16(uint8_t *p, int16_t v)  { put_u16(p, (uint16_t)v); }
static void put_u32(uint8_t *p, uint32_t v)
{
    p[0] = v & 0xFF; p[1] = (v >> 8) & 0xFF; p[2] = (v >> 16) & 0xFF; p[3] = v >> 24;
}

/* dev·slope를 int16으로. 값이 없으면 INT16_MISSING. */
static int16_t scale_x100(float value, bool valid)
{
    if (!valid) return INT16_MISSING;
    float scaled = value * 100.0f;
    if (scaled > 32767.0f)  return 32767;
    if (scaled < -32767.0f) return -32767;
    return (int16_t)scaled;
}

size_t build_frame(uint8_t *out, const sensor_snapshot_t *s)
{
    uint8_t *p = out;

    *p++ = FRAME_VERSION;
    *p++ = s->flags;
    *p++ = 0x00;                       /* present — 선택 블록 없음 */
    memcpy(p, s->mac, 6); p += 6;
    put_u16(p, s->seq); p += 2;
    put_u32(p, s->uptime_s); p += 4;
    *p++ = s->state;

    put_i16(p, scale_x100(s->voc_dev,      s->voc_valid));   p += 2;
    put_i16(p, scale_x100(s->voc_slope,    s->voc_slope_ok)); p += 2;
    put_i16(p, scale_x100(s->h2_dev,       s->h2_valid));    p += 2;
    put_i16(p, scale_x100(s->h2_slope,     s->h2_slope_ok));  p += 2;
    put_i16(p, scale_x100(s->co_dev,       s->co_valid));    p += 2;
    put_i16(p, scale_x100(s->co_slope,     s->co_slope_ok));  p += 2;
    put_i16(p, scale_x100(s->pressure_dev, s->pressure_valid)); p += 2;
    put_u16(p, s->sig_hold_s); p += 2;

    uint16_t crc = crc16_ccitt_false(out, (size_t)(p - out));
    put_u16(p, crc); p += 2;

    return (size_t)(p - out);          /* 34 */
}

/* base64url, 패딩 제거 */
size_t encode_payload(const uint8_t *frame, size_t len, char *out, size_t out_size)
{
    size_t written = 0;
    mbedtls_base64_encode((unsigned char *)out, out_size, &written, frame, len);
    while (written > 0 && out[written - 1] == '=') { --written; }
    for (size_t i = 0; i < written; ++i) {
        if (out[i] == '+') out[i] = '-';
        else if (out[i] == '/') out[i] = '_';
    }
    out[written] = '\0';
    return written;
}

/* AT+SEND=<수신기 주소>,<길이>,<payload> */
```

## 무선 파라미터

노드와 서버가 **전부** 같아야 한다. 하나만 달라도 수신이 0이 되고, 0은 에러가 아니라
침묵이라 원인을 되짚기 어렵다.

| 항목 | 값 | AT 명령 |
|---|---|---|
| 주파수 | **922000000** | `AT+BAND=922000000` |
| SF / BW / CR / Preamble | 9 / 125kHz / 4:5 / 12 | `AT+PARAMETER=9,7,1,12` |
| NETWORKID | 18 | `AT+NETWORKID=18` |
| 노드 주소 | 1 | `AT+ADDRESS=1` |
| **수신기(Pi) 주소** | **2** | 노드는 `AT+SEND=2,...` |
| Baud | 115200 | |

현재 펌웨어의 `915000000`은 **한국 ISM 대역(917~923.5MHz) 밖이다.** 922MHz로 맞춘다.

## 참조 구현

- 서버 파서: `app/infrastructure/lora/frame.py`
- 서버 수신: `app/infrastructure/lora/rylr/`
- 노드 인코더: 위 §노드 참조 구현

## 미확정

| 항목 | 상태 |
|---|---|
| GPS 모듈 | 미장착. `present.gps=0`이면 서버는 좌표 없이 정상 처리한다 |
| 온습도 센서 | 미장착. `present.env=0` |
| 배터리 모니터 | 미장착. `present.power=0` |
| 노드 시각 | 시계 없음. `time_is_epoch=0`이고 서버가 수신 시각을 기록한다 |
