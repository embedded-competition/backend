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
| 경로 | `/api/v1/devices` | `/devices/{deviceId}/...` (버전 prefix 없음) |
| 에러 바디 | `{code, message, request_id, detail}` | `{"error": "device_not_found"}` |
| 필드 명명 | snake_case | **camelCase** (`devZ`, `battMv`, `lastSeen`) |
| 성공 바디 | 래핑 | 리소스 그대로 |

에러 바디에 `request_id`를 추가로 넣는다 — 앱은 `error` 키만 읽으면 되므로 호환이 깨지지 않고, 서버 로그 대조에 필요하다.

### A2. deviceToken 인증 도입

`security.md`에 "미도입 부채"로 적어둔 항목을 해소한다.

- `POST /devices`가 MAC 등록과 함께 토큰 발급
- 이후 모든 요청에 `Authorization: Bearer <deviceToken>`
- 만료 없음, 재등록 시 새 토큰 발급하되 기존 토큰 무효화 안 함 (앱 spec §인증, O4 단일기기 전제)
- 서버는 **토큰 원문을 저장하지 않는다** — SHA-256 해시만 보관. 유출 시 피해 범위를 줄인다
- 기기당 토큰 여러 개를 허용하므로 별도 테이블(`access_tokens`)

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

## 반영 상태

| 항목 | 상태 |
|---|---|
| A1 URL·에러·camelCase | 컨벤션 개정 + 구현 |
| A2 deviceToken | 스키마 + 구현 |
| A3 Expo Push / push_tokens rename | 스키마 |
| A4 events.description | 스키마 + 구현 |
| B1~B3 | **앱 팀 회신 대기** — 회신 전까지 서버는 노드 판정 전제로 진행 |
| C1~C2 | **임베디드 팀 조정 대기** — 서버는 nullable로 받아 영향 차단 |
