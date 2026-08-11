# Pi 되살리기 — 장소를 옮겼을 때

새 장소로 옮기면 Pi는 그 망의 와이파이 프로필이 없어 어디에도 붙지 못한다. SSH도 터널도
죽으므로 **물리 접근이 유일한 경로**다. FTDI 시리얼 콘솔로 들어가 와이파이를 등록한다.

배포·인그레스 설계는 [deployment.md](deployment.md), 터널 셋업은 [cloudflare-setup.md](cloudflare-setup.md).

## 이 문서가 필요한 상황인지 판별

```bash
curl -sS -m 10 -o /dev/null -w '%{http_code}\n' https://api.agenthub.work/health
```

| 결과 | 상태 |
|---|---|
| `200` | Pi 정상. 이 문서 필요 없다 |
| `530` / `1033` | **Pi가 망에 못 붙었다.** 이 문서대로 진행 |
| `502` | 터널은 살아 있고 백엔드만 죽었다 → `systemctl status orca-backend` |

`ping pi.local`은 판별에 쓰지 않는다. 아래 "함정" 참조.

## 1. 배선 (FTDI ↔ Pi)

3선만 쓴다.

| FTDI | Pi 물리 핀 | 신호 |
|---|---|---|
| RX | **8번** | GPIO14 / TX |
| TX | **10번** | GPIO15 / RX |
| GND | **6번** | GND |

**TX↔RX는 교차한다.** 같은 이름끼리 연결하면 안 된다.

**FTDI의 VCC는 연결하지 않는다.** Pi에 별도 전원이 들어와 있으면 역급전이 되고, 5V FTDI면
Pi의 GPIO가 손상된다.

Pi 전원은 micro-USB 두 개 중 **바깥쪽 `PWR` 포트**에 꽂는다. 안쪽은 데이터용이다.

## 2. Mac에서 콘솔 열기

```bash
ls /dev/cu.usbserial-*        # 예: /dev/cu.usbserial-A50285BI
```

안 나오면 FTDI가 인식되지 않은 것이다 — 케이블·포트를 먼저 본다.

**터미널 앱에서 직접** 실행한다.

```
screen /dev/cu.usbserial-A50285BI 115200
```

보율은 **115200**이다. 포트를 처음 열 때 깨진 바이트 몇 개가 나오는 것은 잔여물이고
보율 문제가 아니다 — 엔터를 한 번 더 치면 정상 문자가 나온다.

빠져나올 때는 **`Ctrl-A` → `K` → `y`**.

## 3. 함정

이 다섯 개가 실제로 시간을 잡아먹은 것들이다.

| 증상 | 실제 원인 |
|---|---|
| 키를 쳐도 화면에 안 찍힌다 | **시리얼 콘솔은 로컬 에코가 없다.** 상대가 되돌려주는 것을 보는 것이라, 안 찍히면 입력이 아니라 **Pi가 응답을 안 하는 것**이다 |
| `Password:`에서 아무것도 안 나온다 | 정상이다. 별표도 안 찍힌다. 그대로 치고 엔터 |
| `cu: Line in use` | 이전 `screen`이 detached로 살아 포트를 잡고 있다. `screen -ls`로 찾아 `screen -S <id> -X quit` |
| `screen`이 PTY를 못 찾는다 | 에이전트 셸 등 실제 터미널이 아닌 곳에서 실행했다. 터미널 앱에서 직접 띄운다 |
| `sudo cu` 후 계속 락이 걸린다 | `/dev/cu.*`는 사용자 권한으로 열린다. `sudo`를 붙이면 락 소유자가 root가 된다 |

`Ctrl-A` `D`(detach)로 나오지 않는다. 포트를 계속 물고 있어 다음 접속이 전부 막힌다.

## 4. Pi가 살아 있는지 판별

화면이 비어 있을 때, 전원 문제인지 배선 문제인지 가른다.

**초록 LED**

| LED | 의미 |
|---|---|
| 꺼짐 | 전원이 안 들어온다. 시리얼은 볼 것도 없다 |
| 켜져만 있음 | 전원은 오는데 부팅 실패 (SD카드 의심) |
| 불규칙 깜빡임 | 동작 중 → 배선(특히 Pi 8번 핀) 의심 |

**부팅 로그 캡처** — getty 상태와 무관하게 커널이 직접 뿌리므로 링크 검증에 가장 확실하다.
`screen`을 켜둔 채 전원을 뽑았다 5초 뒤 다시 꽂는다. 로그가 쏟아지면 배선은 정상이다.

`screen`이 포트를 잡고 있어 따로 캡처할 수 없을 때는 읽기 오프셋으로 대신 확인한다.

```bash
lsof /dev/cu.usbserial-A50285BI     # 출력의 SIZE/OFF 값
```

전원 사이클 전후로 이 값이 수만 단위로 뛰면 부팅 로그가 흘러든 것이다.

## 5. 로그인 + 와이파이 등록

계정은 `user`.

```bash
nmcli device wifi list
```

**`CHAN`이 1~13인 SSID만 쓸 수 있다.** 36 이상은 5GHz이고 Pi Zero 2W는 잡지 못한다.

```bash
sudo nmcli --ask device wifi connect '<SSID>'
```

`--ask`는 비밀번호를 셸 히스토리에 남기지 않는다. SSID는 작은따옴표로 감싼다 — `@` 같은
문자가 들어가면 셸이 먹는다.

**한글 SSID는 시리얼 콘솔에서 입력할 수 없다.** IME가 없다. BSSID로 우회한다.

```bash
nmcli -f BSSID,SSID,CHAN,SIGNAL device wifi list
sudo nmcli --ask device wifi connect AA:BB:CC:DD:EE:FF
```

한 번 붙은 망은 프로필로 저장되어 다음부터 자동 연결된다. 재부팅해도 유지된다.

```bash
nmcli connection show          # 저장된 프로필 목록
```

## 6. 확인

```bash
ip -4 addr show wlan0 | grep inet
```

Mac에서:

```bash
curl -sS https://api.agenthub.work/health
```

터널이 자동으로 안 붙으면 Pi에서 한 줄이면 된다.

```bash
sudo systemctl restart cloudflared
```

**공개 주소는 망이 바뀌어도 그대로다.** Pi의 IP가 어디에도 기록되지 않기 때문이며,
D2가 Cloudflare Tunnel을 고른 이유가 이것이다. 앱은 아무것도 바꾸지 않는다.

## 7. `pi.local`을 신뢰하지 않는다

망에 따라 `.local` 조회가 ISP 리졸버에 가로채여 **엉뚱한 공인 IP를 돌려준다.**
실제로 한 장소에서 `pi.local`이 `218.38.137.27`로 해석됐다.

```bash
dscacheutil -q host -a name pi.local     # 공인 IP가 나오면 하이재킹된 것
```

로컬 접속은 장소마다 되기도 하고 안 되기도 한다. **터널이 유일하게 장소에 무관한 경로다** —
D3가 배포 경로를 SSH over Access로 정한 이유와 같다.

## 다음번에 이 절차를 건너뛰는 법

폰 핫스팟을 **미리** 프로필로 등록해두면 새 장소에서 FTDI를 꺼낼 일이 없다.

```bash
sudo nmcli --ask device wifi connect '<핫스팟이름>'
sudo nmcli connection modify '<집SSID>' connection.autoconnect-priority 10
sudo nmcli connection modify '<핫스팟이름>' connection.autoconnect-priority 1
```

새 장소에서는 핫스팟만 켜면 Pi가 스스로 붙고, 터널이 살아나면 **원격에서 그 장소의
와이파이를 등록**할 수 있다. 시리얼 콘솔이 경로에서 빠진다.

핫스팟 이름은 **영문**으로 두는 편이 낫다 (위 한글 제약). iPhone은 **설정 → 개인용 핫스팟 →
「최대 호환성」**을 켜야 2.4GHz로 내려와 Pi가 볼 수 있다.
