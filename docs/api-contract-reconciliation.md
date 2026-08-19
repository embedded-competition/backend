# 앱 ↔ 서버 계약 정합화

대상: [`embedded-competition/app`](https://github.com/embedded-competition/app)의 `api-spec.md`(Draft) + `scooter-app/docs/interface.md`(Draft).
백엔드가 이미 확정한 설계: [`db-schema.md`](db-schema.md).

두 문서가 각각 독립으로 작성돼 전제가 어긋난 지점이 있다. 이 문서가 조정 결과 SSOT다.

## 요약

| 구분 | 건수 |
|---|---|
| 서버가 앱에 맞춘다 | 4 |
| 앱 문서를 고쳐야 한다 | 3 |
| 앱·임베디드 문서끼리 모순 (제3자 조정 필요) | 2 |

---

## A. 서버가 앱에 맞춘다 (백엔드 작업)

### A1. URL·에러 형식·필드 명명을 앱 spec 기준으로

앱이 이미 그 전제로 구현돼 있고, 서버가 맞추는 쪽이 전체 지연이 적다.

| 항목 | 기존 서버 컨벤션 | 확정 |
|---|---|---|
| 경로 | `/api/v1/devices` | `/devices/{mac}/...` (버전 prefix 없음, A2에서 개정) |
| 에러 바디 | `{code, message, request_id, detail}` | `{"error": "device_not_found"}` |
| 필드 명명 | snake_case | **camelCase** (`devZ`, `battMv`, `lastSeen`) |
| 성공 바디 | 래핑 | 리소스 그대로 |

에러 바디에 `request_id`를 추가로 넣는다 — 앱은 `error` 키만 읽으면 되므로 호환이 깨지지 않고, 서버 로그 대조에 필요하다.

### A2. deviceToken 인증 도입 → **철회. MAC 직접 주소화** 🔴

한 번 구현했다가 앱 팀 요구로 되돌렸다. 이 항목은 기록으로 남긴다 — 되돌린 결정을
지우면 왜 지금 인증이 없는지 다음 사람이 알 수 없다.

**확정**: `deviceId`도 `deviceToken`도 없다. **MAC이 곧 식별자이자 유일한 키**다.

- `POST /devices` 삭제. 기기는 **첫 프레임이 만든다**
- 모든 경로가 `/devices/{mac}/...`. `AA:BB:CC:DD:EE:FF`와 `aabbccddeeff` 둘 다 받는다
- `Authorization` 헤더 없음
- 없는 MAC은 404 `device_not_found`

**대가**: MAC을 아는 사람은 누구나 그 킥보드의 센서·위치를 읽고 경보를 해제할 수 있다.
사용자가 트레이드오프를 보고 고른 결정이다. 앱 플로우가 짧아지는 것이 이유다.

`access_tokens` 테이블과 `devices.public_id` 컬럼은 **남긴다** — 마이그레이션이
forward-only Expand-Contract라 쓰기를 멈추는 것까지가 이번 범위다.

### A3. Expo Push로 전환

FCM/APNs 직접 호출이 아니라 Expo Push API를 부른다 (`ExponentPushToken[...]`).
`notification/push.md`의 어댑터 경계는 그대로 유효 — `PushSender` Protocol 구현체만 Expo용으로 만든다.

기존 테이블 `device_tokens`는 이름이 인증 토큰과 헷갈리므로 **`push_tokens`로 rename**한다.

### A4. events.description은 서버가 생성

기록 탭 문장("정상 → 주의 전환")은 서버가 만든다.

**단, 채널 카드 표시 문구(`copy.msg`·`sub`·`easy` 등)는 범위 밖이다.** `interface.md` §3.1이 제기한 C5 확대 적용은 지금 하지 않는다 — 시연 일정 대비 범위가 크고, 앱 목데이터로 충분하다. 재론 시점은 문구 수정이 스토어 심사에 실제로 걸릴 때.

---

## B. 앱 문서를 고쳐야 한다 (앱 팀 요청)

### B1. O2 뒤집기 — signature는 **노드**가 계산한다 🔴

`api-spec.md`: "`signature`는 서버가 raw 데이터로 계산해서 항상 채워 보낸다 — 노드가 직접 계산해서 보내는 게 아니다."

**이 전제는 성립하지 않는다.** 서버가 계산하려면 raw 시계열이 서버에 있어야 하는데, LoRa로 raw를 나를 수 없다:

- SF7/BW125 실효 수 kbps + ISM 대역 duty cycle 규제
- 알고리즘이 요구하는 건 1Hz 샘플링 기반 60초 링버퍼 회귀 (`gas-detection-algorithm-design.md` §2.3)
- 1Hz raw를 무선으로 올리는 건 대역폭·전력 양쪽에서 불가능

임베디드 알고리즘 문서는 이미 상태기계를 **노드에** 두고 설계돼 있다(§3 상태기계, `channel_t` 구조체, `tick_1hz`). signature 3요소(급변·지속·무회복)는 그 계산의 중간 산출물이라 노드가 이미 갖고 있다 — 보내기만 하면 된다.

**요청**: O2를 "노드가 계산해 전송"으로 정정. 앱 화면은 영향 없음 (`signature`가 채워져 오는 건 동일).

### B2. raw 필드 제거 또는 옵셔널 유지 🔴

B1의 귀결. 아래 필드는 서버가 채울 수 없다:

| 필드 | 앱 문서 상태 | 실제 |
|---|---|---|
| `gas.sraw` | "있음" | 전송 안 함 |
| `gas.baseline` | "있음" | 전송 안 함 (노드 내부 상태) |
| `h2.mv` | "있음" | 전송 안 함 |
| `h2.mvAvg` | "있음" | 전송 안 함 |
| `h2.rsKohm` | "있음" | 전송 안 함 |
| `co.mv` | 미착수 | 전송 안 함 |

**요청**: `RawValuesDisclosure` 컴포넌트(원본수치 접이식)를 `devZ`·`slope` 기준으로 바꾸거나 숨긴다. 타입에서 optional로 내린다.

**대안이 있다면** 벤치 튜닝용 raw는 노드를 USB 직결한 시리얼 로거로 뽑는다 — 무선 경로와 분리된 채널이다.

### B3. 폴링 주기가 데이터 갱신 주기와 안 맞는다 🟡

`api-spec.md`: "NORMAL 10초 / WATCH·ALARM 1초 간격 폴링".

LoRa 업링크는 duty cycle 제약상 1초 간격이 불가능하다. ALARM 시 노드가 고빈도로 전환해도 초 단위는 못 간다. 1초 폴링하면 **같은 값을 반복해서 받는다**.

**요청**: 폴링 주기를 낮추고(예: NORMAL 30초 / WATCH·ALARM 5초), 서버가 내려주는 `module.lastSeen`으로 **데이터 나이**를 화면에 표시한다. 그래야 "무선 두절"과 "값이 안 변함"을 사용자가 구분한다.

서버는 `lastSeen`을 항상 채워 보낸다.

---

## C. 앱·임베디드 문서끼리 모순 (백엔드 범위 밖, 조정 필요)

### C1. "LoRa 14B 페이로드"에 요구 필드가 안 들어간다

`interface.md`가 `module`을 "LoRa 14B 페이로드 기반"이라 적었는데, 같은 문서가 요구하는 필드 합계는 그보다 훨씬 크다.

| 그룹 | 최소 바이트 |
|---|---|
| nodeId 2 + seq 1 + state 1 + battMv 2 | 6 |
| gas dev·slope (2+2) | 4 |
| h2 dev·slope (2+2) | 4 |
| signature (플래그 3 + holdS 2) | 3 |
| GPS lat·lon (float32 ×2) | 8 |
| env tempC·rh | 4 |
| CRC | 2 |

raw를 다 뺀 최소 구성으로도 **31B**. GPS만 8B다.

선택지: ① 페이로드를 늘린다(전송 시간·전력 증가, duty cycle 예산 소모) ② GPS를 상태 전이 시에만 싣는다(heartbeat에선 생략) ③ GPS를 폰 위치로 대체한다.

**추천은 ②** — 킥보드가 주차 중엔 안 움직이므로 좌표를 매번 보낼 이유가 없다. heartbeat는 좌표 없이, 전이 프레임에만 포함.

### C2. GPS 확정(O1)과 하드웨어 BOM

O1이 "임베디드 모듈이 직접 측정"으로 확정됐는데, 지금 노드 구성(ESP32-C3 + 가스센서)에 GPS 모듈이 BOM에 있는지 확인 필요. 없으면 O1은 아직 결정이 아니라 요구사항이다.

서버는 `location`을 **nullable**로 받는다 — GPS가 붙든 안 붙든 스키마는 안 바뀐다.

---

## D. 도메인 용어 정정

앱은 **킥보드(scooter)**, 백엔드 초기 설계는 전기차를 전제했다. 스키마 구조는 동일("노드 1개 = 이동수단 1대")이라 컬럼 변경은 없고 문서 용어만 정정한다.

`db-schema.md`의 "차량" → "킥보드"로 통일.

---

## E. v1 계약 개편

### E1. 모든 도메인 경로에 `/v1` 접두

`/health`·`/docs`는 운영용이라 버전 밖에 둔다. 나머지는 전부 `/v1/devices/{mac}/...`.

### E2. `telemetry/summary` → `telemetry/current` + `telemetry/peaks`

`live` boolean 하나로 "지금 값"과 "기간 중 최고치"라는 서로 다른 두 응답을 겸하던 것을 쪼갰다.
`current`는 구간 개념 자체가 없고(from/to 파라미터 없음), `peaks`는 from/to를 받되 에코백하지 않는다
(서버가 손대지 않는 값이라 클라가 이미 안다). 부수 효과로, `_live` 경로가 period를 무시하고
`readings.latest()`를 그대로 돌려주던 버그가 `current`에는 period 자체가 없어져 구조적으로 사라졌다.

### E3. `state` → `status` + `conditions[]`

`AlertState`(WARMUP/NORMAL/WATCH/ALARM/FAULT) 하나가 "사용자가 취해야 하는 상태"와
"기기에 무슨 일이 일어나는가"라는 두 축을 접고 있었다. 후자를 `Condition`
(`CO_RISE`/`H2_RISE`/`VOC_RISE`/`PRESSURE_RISE`/`WATER`/`SENSOR_FAULT`/`UNKNOWN`)으로 분리해
배열로 내려준다 — 여러 원인이 동시에 성립할 수 있어서다. `status`는 기존 `state`와 같은 값·같은
도출 규칙을 유지한다.

**호환 규칙**: `TEMP_RISE`·`RAPID_WORSENING`·`IGNITION`은 프레임 v2에서 추가될 예정이라 지금은
만들지 않는다. **클라는 모르는 `conditions` 값을 무시해야 한다** — 나중에 값이 늘어도 이 계약이
깨지지 않게 하기 위해서다.

**`UNKNOWN`**: 노드가 매핑표에 없는 ALERT 원인을 보내면 프레임을 버리지 않고 `UNKNOWN`으로
흡수한다(서버 로그에 원본 문자열을 남겨 다음 배포에서 정확한 값으로 승격한다). 펌웨어와 서버는
따로 배포되므로 이 상황은 예정된 일이다 — 그 순간 프레임을 버리면 새 이상이 감지된 바로 그
때 센서 값까지 함께 사라진다. `status`엔 WATCH로 반영되고(`SENSOR_FAULT`가 아닌 원인이므로),
클라는 `UNKNOWN`도 위 호환 규칙에 따라 무시하면 된다.

### E4. `telemetry/history` → `sensors/{sensor}/detail`

여러 채널을 한 번에 담던 `history`를 채널 하나만 보는 `sensors/{sensor}/detail`로 쪼갰다
(`sensor` ∈ `gas|h2|co|pressure|temp|rh`). 칸(`bucket`)에서 `state`·`samples`·`events`를 뺐다 —
단일 채널에 기기 전체 상태를 붙이면 축이 안 맞고, 기록은 이미 `/events`가 따로 있다.
`interval`도 더 이상 에코백하지 않는다 — 자유 형식 파싱을 닫힌 집합(`5m/15m/30m/1h/2h/6h/12h/1d`)으로
좁혀 서버가 값을 정규화할 일 자체가 없어졌기 때문이다.

### E5. `/events`에 `truncated` 추가

기존엔 200개 상한에서 조용히 잘렸다. `{items, truncated}`로 잘림 여부를 드러낸다.

### E6. `location`의 404를 두 가지로 분리

기기가 없는 것(`device_not_found`)과 좌표를 아직 못 받은 것(`location_unavailable`)은 다른 사건이다.
상태 코드는 둘 다 404로 유지하고, `error` 코드로 구분한다.

---

## 반영 상태

| 항목 | 상태 |
|---|---|
| A1 URL·에러·camelCase | ✅ 구현 완료 |
| A2 deviceToken | ❌ **철회** — MAC 직접 주소화로 대체. 인증 없음 |
| A3 Expo Push / push_tokens rename | ✅ 구현 완료 (자격증명 없으면 LoggingPushSender) |
| A4 events.description | ✅ 구현 완료 (`core/descriptions.py`) |
| A5 응답 평탄화 | ✅ 구현 완료 — `range`·`peaks`·`current` 포장 제거, `devZ`→`value`, 클라 계산 가능 필드 제거 |
| B1~B3 | **앱 팀 회신 대기** — 회신 전까지 서버는 노드 판정 전제로 진행 |
| C1~C2 | **임베디드 팀 조정 대기** — 서버는 nullable로 받아 영향 차단 |
| E1~E6 v1 계약 개편 | ✅ 구현 완료 |
