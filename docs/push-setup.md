# 푸시 알림 셋업

경보를 폰까지 보내는 경로. **클라 팀과 함께 한 번만 한다.**

이 문서는 절차만 적는다. 서버 코드는 이미 있고 손댈 것이 없다.

## 확정값

| 항목 | 값 |
|---|---|
| 앱 스택 | React Native + Expo |
| 전송 방식 | **Expo Push** (`https://exp.host/--/api/v2/push/send`) |
| Android 백엔드 | FCM HTTP v1 (Expo가 대신 호출) |
| iOS 백엔드 | APNs (Expo가 키까지 관리) |
| 서버 어댑터 | `app/infrastructure/push/expo.py` |
| 토큰 등록 | `POST /v1/devices/{mac}/push-token` |

## 경로

```
Pi(orca-backend) → exp.host → FCM ─→ Android
                            └ APNs ─→ iOS
```

우리 서버는 Expo까지만 안다. FCM·APNs 호출은 Expo가 한다.

## D1. 왜 FCM 직접이 아니라 Expo Push인가

| | Expo Push | FCM 직접 |
|---|---|---|
| 토큰 | `ExponentPushToken[...]` 하나로 양 플랫폼 | 플랫폼별로 다름 |
| iOS APNs 키 | **Expo가 발급·갱신** | Apple Developer에서 직접 뽑아 업로드 |
| 서버 인증 | 불필요 | 서비스 계정 JSON + OAuth2 토큰 캐시 |
| 홉 | 하나 더 (지연·장애점) | 없음 |
| 추가 의존 | 없음 (`httpx`만) | `google-auth` |

앱이 Expo로 빌드되므로 Expo Push가 맞다. 서버가 이미 `ExpoPushSender`로 구현돼 있어 **추가 작업이 없다.**

전환이 필요해지면 `PushSender` 포트에 `FcmPushSender`를 새로 구현하면 된다 — `NotificationService`는 재시도·토큰 비활성화만 알고 전송 수단은 모른다.

## 0. 사전 확인

Firebase Console에서:

- 프로젝트가 생성돼 있음
- ⚙️ 프로젝트 설정 → **Cloud Messaging** 탭 → `Firebase Cloud Messaging API (V1)`가 **사용 설정됨**
  (아래 Legacy는 비활성이 정상 — 2024년 6월 종료됨)

앱 저장소에서:

```bash
grep -E '"expo"|expo-notifications' package.json
```

## 1. 서비스 계정 키 발급

```
⚙️ 프로젝트 설정 → 서비스 계정 탭 → "새 비공개 키 생성" → JSON 다운로드
```

> **이 저장소는 public이다.** JSON을 저장소 안에 두지 않는다. `.gitignore`가 `secrets/`,
> `firebase-adminsdk-*.json`, `*.p8`을 막고 있지만, 애초에 밖에 두는 것이 원칙이다.
> 커밋되면 되돌릴 방법은 키 폐기·재발급뿐이다.

```bash
mkdir -p ~/orca-secrets && chmod 700 ~/orca-secrets
mv ~/Downloads/*firebase-adminsdk*.json ~/orca-secrets/fcm.json
chmod 600 ~/orca-secrets/fcm.json
```

**이 키는 우리 서버가 쓰지 않는다.** 다음 단계에서 Expo에 올린다.

## 2. Expo에 FCM 키 등록 (Android)

SDK 53부터 FCM v1이 필수다. 이걸 안 하면 **Android만 조용히 안 간다.**

```bash
npm install -g eas-cli
eas login
eas credentials
```

```
→ Android
→ Google Service Account
→ "Manage your Google Service Account Key for Push Notifications (FCM V1)"
→ ~/orca-secrets/fcm.json 업로드
```

## 3. iOS APNs (iOS 지원 시에만)

```bash
eas credentials
→ iOS
→ Push Notifications: Manage your Apple Push Notifications Key
→ "Set up a new key"
```

Expo가 Apple Developer 계정에 로그인해 APNs 키를 **자동 발급**한다. 직접 뽑아 올릴 필요 없다.

## 4. 앱 쪽

```
1. expo-notifications로 권한 요청
2. getExpoPushTokenAsync() → ExponentPushToken[...]
3. POST /v1/devices/{mac}/push-token  { "token": "ExponentPushToken[...]" }
```

- 등록은 **멱등**하다. 앱 실행마다 보내도 된다
- 토큰은 앱 재설치·OS 업데이트로 바뀐다. 실행 시마다 재등록하는 것이 맞다
- `data.deviceMac`으로 알림 탭 시 열 기기 화면을 정한다

## 5. 검증

**5-1. 서버 없이 Expo만** — 앱에서 얻은 토큰으로 https://expo.dev/notifications 에서 직접 전송.
폰에 뜨면 Expo↔FCM/APNs 연결이 끝난 것이다. 안 뜨면 2·3단계 문제다.

**5-2. 서버 경유** — 토큰 등록 후 경보를 유발하고 서버 로그 확인:

```bash
ssh -o ProxyCommand="cloudflared access ssh --hostname ssh.agenthub.work" user@ssh.agenthub.work
journalctl -u orca-backend -f | grep -E 'alert dispatched|push'
```

`alert dispatched`에 `delivered` 수가 찍히면 성공이다.

## 서버가 이미 하는 것

| 동작 | 위치 |
|---|---|
| 최대 3회 재시도, 지수 백오프 | `NotificationService._send_with_retry` |
| 영구 실패 시 토큰 비활성화 | `DeviceNotRegistered`, `InvalidCredentials` |
| 전송 이력 기록 | `push_deliveries` 테이블 |
| 상태별 문구 생성 | `app/infrastructure/push/messages.py` |
| `priority: high` | `ExpoPushSender.send` |

`APP_PUSH_DELIVERY=log`면 실제 발송 없이 로그만 남는다. `/health`의 `push` 구성요소가 `DISABLED`로 뜬다.

## 함정

| 함정 | 실체 | 대응 |
|---|---|---|
| **Android Doze** | 화면 꺼지면 배달 지연 | `priority: high` (이미 적용됨) |
| **제조사 배터리 최적화** | 삼성·샤오미가 앱을 죽이면 high priority여도 못 받음 | 앱에서 배터리 최적화 예외 요청 |
| **iOS 무음·집중 모드** | 뚫으려면 Critical Alerts entitlement가 필요하고 **Apple 심사가 있다** | 없으면 `time-sensitive`가 상한 |
| **FCM은 보장 배달이 아니다** | best-effort | 화재 경보를 푸시 단독에 걸지 않는다 |
| Legacy FCM API | 2024년 6월 종료 | server key 방식 문서는 전부 폐기됨 |

**푸시는 보조 경로다.** 배터리 화재에서 알림이 늦으면 시스템이 없는 것과 같다.
현장 부저·경광등처럼 네트워크와 OS에 의존하지 않는 층을 따로 두는 것이 맞다 — 아직 설계되지 않았다.
