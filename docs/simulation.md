# 임베디드 없이 화면 만들기 — 시뮬레이터

실측값이 아직 없어도 앱이 봐야 하는 화면을 전부 만들 수 있다. 스케줄러 하나가 임베디드
노드 자리에 서서 틱마다 프레임을 내보내고, HTTP로 센서별 흐름을 조절한다. 저장·전이·알림은
실기 경로와 같은 코드가 처리한다 — 시뮬레이터는 프레임을 만드는 데까지만 관여한다.

## 켤 것이 없다 — 항상 돌고 있다

설정 키가 없다. 앱이 뜨면 시뮬레이터도 뜬다. 로컬이든 Pi든 같다. 끄고 켜는 것은 배포가
아니라 실행 중에 `PATCH /v1/simulation`으로 한다.

무선 수신기와 나란히 돈다. `APP_LORA_SOURCE`(`none` / `sx1276` / `rylr`)는 무선 쪽만
정하고 시뮬레이터에는 영향이 없다. 둘은 생존도 따로 센다 — 시뮬레이터가 틱을 내도
`/health`의 `lora_radio`는 실기 노드가 조용하면 조용하다고 답한다.

기본 틱은 3초, 기기는 다섯 대다.

테스트 기기의 MAC은 `00:00:00:00:00:01`부터 차례로 붙는다. 이 접두사는 제조사 OUI가
아니라 실기기와 절대 겹치지 않는다. `scripts/seed_demo.py`가 쓰는 시연 기기와 같은
MAC이라, 시연 데이터를 채운 기기 위에 실시간 흐름을 얹을 수 있다.

## 눈금은 0~1000이고, 어디를 넘느냐가 화면을 정한다

노드가 보내는 값과 같은 스케일이다(`docs/lora-frame.md`). 채널마다 조건이 서는 눈금과
경보로 latch되는 눈금이 다르다.

| 채널 | 기준선 | 조건이 서는 눈금 | 경보 눈금 | 넘으면 서는 조건 |
|---|---|---|---|---|
| `co` | 80 | 400 | 750 | `CO_RISE` |
| `h2` | 90 | 400 | 750 | `H2_RISE` |
| `voc` | 120 | 450 | 800 | `VOC_RISE` |
| `pressure` | 110 | 400 | 780 | `PRESSURE_RISE` |
| `water` | 30 | 300 | 없음 | `WATER` |

눈금 1000에 닿으면 포화로 본다. 포화는 위험이 아니라 불신이라 경보가 아니라
`SENSOR_FAULT`가 되고, 화면은 센서 점검 필요로 바뀐다. 그래서 경보를 보려면 1000이 아니라
경보 눈금과 1000 사이에 세워야 한다.

경보는 틱에서 한 번 걸리면 값을 내려도 풀리지 않는다(latch). 푸는 방법은 리셋뿐이다.

## 엔드포인트는 네 개다

모두 `/v1/simulation` 아래에 있고, 인증은 없다.

| 메서드 | 경로 | 하는 일 |
|---|---|---|
| `GET` | `/v1/simulation` | 스케줄러와 노드 전체 상태 |
| `PATCH` | `/v1/simulation` | 틱 발신 on/off, 틱 간격 |
| `POST` | `/v1/simulation/devices/{mac}/channels/{channel}/flow` | 센서 하나의 흐름 지시 |
| `POST` | `/v1/simulation/devices/{mac}/reset` | 기준선 복귀 + latch 해제 |

흐름 지시의 몸체는 세 값이다.

```json
{ "direction": "rise", "amount": 400, "overSeconds": 30 }
```

- `direction` — `rise`(오르는 흐름) 또는 `fall`(내리는 흐름)
- `amount` — 옮길 눈금 폭. 0~1000 스케일이고 범위 밖은 잘린다
- `overSeconds` — 이 시간에 걸쳐 선형으로 옮긴다. `0`이면 즉시

진행 중인 흐름에 새 지시를 주면 원래 출발점이 아니라 **지금 위치**에서 다시 출발한다.
값이 튀지 않는다.

## 화면별로 이렇게 만든다

```bash
BASE=http://localhost:8000/v1/simulation
MAC=00:00:00:00:00:01

# 주의 (가스 누출) — 30초에 걸쳐 CO를 400 올린다
curl -X POST "$BASE/devices/$MAC/channels/co/flow" \
  -H 'content-type: application/json' \
  -d '{"direction":"rise","amount":400,"overSeconds":30}'

# 경보 (신고) — 경보 눈금 위, 포화 아래로 세운다
curl -X POST "$BASE/devices/$MAC/channels/h2/flow" \
  -H 'content-type: application/json' \
  -d '{"direction":"rise","amount":800,"overSeconds":10}'

# 센서 점검 필요 — 포화시킨다
curl -X POST "$BASE/devices/$MAC/channels/voc/flow" \
  -H 'content-type: application/json' \
  -d '{"direction":"rise","amount":1000,"overSeconds":0}'

# 침수
curl -X POST "$BASE/devices/$MAC/channels/water/flow" \
  -H 'content-type: application/json' \
  -d '{"direction":"rise","amount":400,"overSeconds":0}'

# 되돌리기
curl -X POST "$BASE/devices/$MAC/reset"
```

지금 어디까지 왔는지는 `GET /v1/simulation`이 답한다. 채널마다 지금 눈금·목표·남은 시간과
조건이 서는 눈금을 함께 준다.

```bash
curl -s "$BASE" | jq '.nodes[0] | {state, conditions, latched,
  channels: [.channels[] | {channel, level, target, secondsLeft, condition}]}'
```

값이 앱 화면까지 도달했는지는 제품 API로 확인한다.

```bash
curl -s "http://localhost:8000/v1/devices/$MAC/telemetry/current" | jq
```

## 흐름을 바꿔도 저장은 틱에서만 일어난다

지시는 즉시 반영되지만 판독이 남는 시점은 다음 틱이다. 기본 3초라 보통은 티가 안 나지만,
틱을 길게 잡아 두면 화면이 안 바뀐다고 오해하기 쉽다. 급할 때는 틱을 줄인다 — 대기 중이던
틱이 즉시 깨지고 바로 다음 틱이 돈다.

```bash
curl -X PATCH "$BASE" -H 'content-type: application/json' -d '{"tickSeconds":1}'
curl -X PATCH "$BASE" -H 'content-type: application/json' -d '{"running":false}'
```

조절은 프로세스가 살아 있는 동안만 유지된다. 재기동하면 3초·가동 상태로 돌아온다.

## 켜 둔 채 방치하면 SD카드가 먼저 죽는다

기본 틱으로 하루 **14.4만 행**이 쌓인다(3초 × 5대). Pi Zero 2W의 SD카드이고 readings에
보존 정책이 없다. 시연이 끝났으면 멈추거나 틱을 늘려 둔다.

```bash
curl -X PATCH "$BASE" -H 'content-type: application/json' -d '{"running":false}'
```

쌓인 것을 지울 때는 시뮬레이션분만 골라낼 수 있다 — 아래 `frame_version`.

## 시뮬레이터가 만든 판독은 실측이 아니라고 표시된다

저장된 행의 `frame_version`이 `100`이다. 와이어 포맷(`1`)·노드 CSV(`0`)와 겹치지 않으므로
나중에 실측만 골라내거나 시뮬레이션분만 지울 수 있다.

시뮬레이터는 실기 노드와 다른 payload를 쓴다. 와이어 프레임 v1에는 상태 바이트가 없어
파서가 늘 `NORMAL`을 쓰기 때문이다 — 그 포맷으로 시뮬레이션하면 값만 오르내리고 화면은
영원히 정상이라, 만들려던 화면을 하나도 만들지 못한다. 그래서 노드가 이미 갖고 있는
판정(상태·조건·latch)을 그대로 싣는 별도 payload를 쓴다. 프레임 v2가 나르기로 한 것과
같은 내용이다.

제어 endpoint는 `docs/openapi.json`에 함께 실린다. 모든 배포에 존재하므로 스펙이 그렇게
말하는 것이 사실에 맞다. 앱이 부를 계약은 아니고 `simulation` 태그로 묶여 있다.
