# Cloudflare Tunnel 셋업

Pi를 공개 인터넷에 붙이고 GitHub Actions가 SSH로 닿게 하는 절차. **한 번만 한다.**

왜 이 방식인지는 [deployment.md](deployment.md)의 D2(인그레스)·D3(배포 경로).
이 문서는 그 결정을 실행하는 순서만 적는다.

## 확정값

아래 값들이 이 문서 전체에서 쓰인다.

| 항목 | 값 |
|---|---|
| 도메인 | `agenthub.work` (Cloudflare Registrar) |
| 터널 이름 | `embedded` |
| API 호스트네임 | `api.agenthub.work` → `http://localhost:8000` |
| SSH 호스트네임 | `ssh.agenthub.work` → `ssh://localhost:22` |
| Pi 계정 | `user` |
| Pi 로컬 접속 | `ssh user@pi.local` |
| 저장소 경로 | `/home/user/backend` |
| 백엔드 서비스 | `orca-backend` (systemd) |

## 0. 사전 확인

Cloudflare 대시보드에서:

- `agenthub.work`가 zone으로 등록되고 상태가 **Active**
- DNS Records에 `api` / `ssh` 이름이 **비어 있음** — 이미 있으면 3단계가 실패한다

Pi에서:

```bash
ssh user@pi.local
uname -m          # aarch64 여야 한다. armv7l이면 D7대로 64비트 재설치
```

## 1. Tailscale 제거

설치한 적 없으면 건너뛴다.

**로그아웃을 purge보다 먼저 한다.** 패키지를 먼저 지우면 데몬이 없어 노드 인증을 해제하지
못하고 관리 콘솔에 유령 머신이 남는다.

```bash
sudo tailscale down
sudo tailscale logout

sudo systemctl disable --now tailscaled
sudo apt purge -y tailscale
sudo apt autoremove -y

sudo rm -rf /var/lib/tailscale
sudo rm -f /etc/default/tailscaled
sudo rm -f /etc/apt/sources.list.d/tailscale.list
sudo rm -f /usr/share/keyrings/tailscale-archive-keyring.gpg
sudo apt update
```

확인 — 셋 다 비어야 한다.

```bash
which tailscale
systemctl status tailscaled
ip link | grep tailscale
```

마지막으로 <https://login.tailscale.com/admin/machines>에서 Pi 머신 삭제.

노트북에도 깔았으면 `brew uninstall --cask tailscale` 또는 Applications에서 앱 삭제.

## 2. cloudflared 설치 (Pi)

```bash
curl -L -o /tmp/cloudflared.deb \
  https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64.deb
sudo dpkg -i /tmp/cloudflared.deb
cloudflared --version
```

## 3. 터널 생성 + DNS 라우트 (Pi)

```bash
cloudflared tunnel login
```

출력된 URL을 **노트북 브라우저에서** 열고 `agenthub.work`를 선택한다. Pi에 브라우저가 없어도
되는 이유다. 성공하면 `~/.cloudflared/cert.pem`이 생긴다.

```bash
cloudflared tunnel create embedded
TUNNEL_ID=$(cloudflared tunnel list | awk '$2=="embedded"{print $1}')
echo "$TUNNEL_ID"       # 비어 있으면 create 실패
```

`~/.cloudflared/<UUID>.json`이 이 터널의 자격증명이다.

```bash
cloudflared tunnel route dns embedded api.agenthub.work
cloudflared tunnel route dns embedded ssh.agenthub.work
```

이 명령이 Cloudflare DNS에 레코드를 **대신 만든다.** 대시보드에서 손으로 추가할 일이 없다.

| Type | Name | Target | Proxy |
|---|---|---|---|
| CNAME | `api` | `<UUID>.cfargotunnel.com` | **Proxied** |
| CNAME | `ssh` | `<UUID>.cfargotunnel.com` | **Proxied** |

`*.cfargotunnel.com`은 공개 DNS에 존재하지 않는 이름이고 Cloudflare 엣지 내부에서만 해석된다.
따라서 **프록시(주황 구름)를 끄면 즉시 죽는다** — 엣지를 안 거치면 이 이름을 풀 리졸버가 없다.

도메인이 Cloudflare Registrar에 있어 네임서버가 이미 위임돼 있다. NS 변경 단계는 없다.

## 4. config.yml (Pi)

catch-all(`http_status:404`)이 없으면 `ingress validate`가 실패한다.

```bash
sudo mkdir -p /etc/cloudflared
sudo tee /etc/cloudflared/config.yml > /dev/null <<EOF
tunnel: $TUNNEL_ID
credentials-file: /home/user/.cloudflared/$TUNNEL_ID.json

ingress:
  - hostname: api.agenthub.work
    service: http://localhost:8000
  - hostname: ssh.agenthub.work
    service: ssh://localhost:22
  - service: http_status:404
EOF

cat /etc/cloudflared/config.yml      # 변수가 실값으로 박혔는지 확인
cloudflared tunnel ingress validate
```

**커밋 금지**: `~/.cloudflared/cert.pem`, `~/.cloudflared/<UUID>.json`.
`config.yml`은 UUID·호스트네임뿐이라 저장소에 둬도 된다.

## 5. 서비스 등록 (Pi)

`cloudflared service install`이 `/etc/systemd/system/cloudflared.service`를 **생성한다.**
unit 파일을 직접 쓰지 않는다.

```bash
sudo cloudflared service install
sudo systemctl enable --now cloudflared
systemctl status cloudflared
```

512MB 예산(D2: 백엔드 220M + cloudflared ~30MB + OS ~120MB)을 지키기 위해 상한을 건다.
생성된 unit을 편집하지 않고 drop-in으로 덮는다 — cloudflared 업데이트가 unit을 덮어써도 남는다.

```bash
sudo mkdir -p /etc/systemd/system/cloudflared.service.d
sudo tee /etc/systemd/system/cloudflared.service.d/memory.conf > /dev/null <<'EOF'
[Service]
MemoryMax=64M
EOF
sudo systemctl daemon-reload && sudo systemctl restart cloudflared
```

## 6. Access — SSH 호스트네임에만

<https://one.dash.cloudflare.com> → Access.

1. **Applications → Add an application → Self-hosted**
   - Application name: `embedded-ssh`
   - Public hostname: `ssh.agenthub.work`
2. **Policy 추가**
   - Action: **`Service Auth`**
   - Include: **Service Token** → Any Access Service Token
3. **Access → Service Auth → Create Service Token**
   - Client ID / Client Secret 발급. **Secret은 이때 한 번만 보인다.**

| 함정 | 결과 |
|---|---|
| Action을 `Allow`로 만듦 | 사람 로그인용이 되어 CI가 못 뚫는다 |
| `api.agenthub.work`에도 Access 적용 | **모바일 앱 요청이 전부 로그인 화면으로 막힌다** |

## 7. 배포 키 + GH Secrets

노트북에서 키를 만들고 Pi에 심는다.

```bash
ssh-keygen -t ed25519 -f ~/.ssh/embedded_deploy -N ""
ssh-copy-id -i ~/.ssh/embedded_deploy.pub user@pi.local
```

Pi의 호스트 키를 고정한다. 없으면 Actions가 매 배포마다 처음 보는 호스트를 그냥 믿게 된다.

```bash
# Pi에서
echo "ssh.agenthub.work $(cut -d' ' -f1,2 /etc/ssh/ssh_host_ed25519_key.pub)"
```

GitHub → 저장소 → Settings → Secrets and variables → Actions:

| Secret | 값 |
|---|---|
| `CF_ACCESS_CLIENT_ID` | 6단계 Client ID |
| `CF_ACCESS_CLIENT_SECRET` | 6단계 Client Secret |
| `DEPLOY_SSH_KEY` | `cat ~/.ssh/embedded_deploy` 전문 (개인키) |
| `DEPLOY_KNOWN_HOSTS` | 위 `echo` 출력 한 줄 |
| `DEPLOY_HOST` | `ssh.agenthub.work` |
| `PUBLIC_HEALTH_URL` | `https://api.agenthub.work/health` |

## 8. 검증

Pi에서:

```bash
id user | grep -o 'spi\|gpio'          # 둘 다 나와야 SPI·GPIO 접근됨
systemctl status orca-backend cloudflared
vcgencmd get_throttled                 # 0x0. 전압 부족은 SD·DB 손상으로 이어진다
curl -fsS localhost:8000/health
```

노트북에서 — **폰 LTE 테더링으로** 하면 터널을 실제로 타는지까지 확인된다.

```bash
dig +short api.agenthub.work           # Cloudflare 엣지 IP. cfargotunnel이 보이면 프록시가 꺼진 것
curl -fsS https://api.agenthub.work/health
curl -s -o /dev/null -w '%{http_code}\n' https://api.agenthub.work/docs   # 404가 정상 (D6)
```

SSH 경로는 노트북에도 cloudflared가 있어야 한다.

```bash
brew install cloudflared

ssh -o ProxyCommand="cloudflared access ssh --hostname %h \
      --service-token-id <CLIENT_ID> \
      --service-token-secret <CLIENT_SECRET>" \
    -i ~/.ssh/embedded_deploy \
    user@ssh.agenthub.work whoami
```

`user`가 출력되면 Actions가 탈 경로가 그대로 뚫린 것이다. 토큰 없이 붙으면 막히는 게 정상이다.

마지막으로 **Pi를 다른 와이파이에 붙였다 떼면서 같은 URL이 그대로 뜨는지** 확인한다.
D2의 전제(Pi IP가 어디에도 기록되지 않는다)가 여기서 실증된다.

## 9. 막히는 지점

| 증상 | 원인 |
|---|---|
| `tunnel ingress validate` 실패 | catch-all `http_status:404` 누락 |
| `route dns` 실패 | 같은 이름의 DNS 레코드가 이미 있음 → 대시보드에서 삭제 |
| 공개 URL이 1033 / 1016 | cloudflared는 떴는데 백엔드가 죽음 → `systemctl status orca-backend` |
| `dig`에 `cfargotunnel.com`이 그대로 | 프록시(주황 구름)가 꺼짐 |
| SSH가 브라우저 로그인 화면 | 정책 Action이 `Allow`. `Service Auth`로 교체 |
| 앱 요청이 전부 로그인으로 감 | `api.agenthub.work`에 Access를 걸었음 |
| `dpkg -i` 아키텍처 오류 | 32비트 OS. D7대로 64비트 재설치 |

## 10. 호스트네임 교체 (프로젝트 이름 확정 후)

하나의 터널이 여러 호스트네임을 동시에 서비스한다. **병행 운영 후 옛 이름을 지운다.**
Pi 재설정도 무중단 전환 설계도 필요 없다.

1. `cloudflared tunnel route dns embedded api.<새이름>`
2. `/etc/cloudflared/config.yml`에 ingress 항목 추가 (catch-all **위에**)
3. `sudo systemctl restart cloudflared`
4. 앱을 새 주소로 빌드·배포 — 이 구간에는 옛 주소와 새 주소가 **둘 다 산다**
5. 스토어 반영 확인 후 옛 ingress 항목·DNS 레코드 삭제
6. GH Secrets의 `DEPLOY_HOST`·`PUBLIC_HEALTH_URL` 갱신

병행 구간이 스토어 심사 기간을 흡수한다. 도메인 만료와 결정적으로 다른 점이다.
