#!/usr/bin/env bash
# Raspberry Pi 배포. 절차는 workflows/backend/deploy-rpi.md.
#
#   ./deploy/deploy.sh <target-commit-or-tag>
#
# 문서에만 적힌 수동 명령 나열을 만들지 않기 위해 스크립트가 SSOT다.
set -Eeuo pipefail

# 비대화형 SSH는 로그인 프로필을 읽지 않는다. uv 설치 경로를 직접 얹는다 —
# 이 경로는 systemd unit의 ExecStart와 같은 전제다.
PATH="$HOME/.local/bin:$PATH"
export PATH

REPO_DIR="${DEPLOY_REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

# 아래 2단계의 checkout이 이 파일 자체를 갈아치운다. bash는 스크립트를 필요할 때마다
# 이어 읽으므로, 그대로 두면 옛 버전과 새 버전이 한 번의 실행 안에서 섞인다.
# 저장소 밖 사본으로 옮겨 실행해 그 창을 없앤다.
#
# 그 대가: 사본은 checkout 전에 떠지므로 이 스크립트를 고친 배포는 여전히 옛
# 스크립트로 실행된다. deploy.sh 변경은 항상 한 배포 늦게 효력이 생긴다.
# 배포 절차를 바꿨는데 안 먹었으면 버그가 아니라 이것이니, 한 번 더 배포한다.
if [ -z "${DEPLOY_DETACHED:-}" ]; then
    _copy="$(mktemp)"
    cat "${BASH_SOURCE[0]}" > "$_copy"
    DEPLOY_DETACHED="$_copy" DEPLOY_REPO_DIR="$REPO_DIR" exec bash "$_copy" "$@"
fi

# 어떤 경로로 죽든 되돌린다. ERR 트랩만으로는 명시적 exit 1을 못 잡는다.
# 되돌릴 지점을 기록하기 전에는 롤백할 대상이 없으므로 무장하지 않는다.
on_exit() {
    exit_code=$?
    rm -f "$DEPLOY_DETACHED"
    [ "$exit_code" -eq 0 ] && exit 0
    if [ -n "${ROLLBACK_ARMED:-}" ]; then
        echo
        echo "== 배포 실패 (exit $exit_code) — 자동 롤백 =="
        "$REPO_DIR/deploy/rollback.sh" || echo "롤백도 실패했다. 수동 개입이 필요하다."
    fi
    exit "$exit_code"
}
trap on_exit EXIT

TARGET="${1:?배포할 커밋 또는 태그를 지정해야 한다}"
SERVICE=orca-backend
DB_PATH="${APP_DATABASE_PATH:-$REPO_DIR/data/orca.db}"
BACKUP_DIR="$REPO_DIR/data/backups"
MANIFEST="$BACKUP_DIR/last-deploy.env"
RELEASE_FILE="$REPO_DIR/data/release.env"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

cd "$REPO_DIR"

# 되돌릴 지점을 파일로 남긴다. 이 프로세스가 죽어도 rollback.sh가 읽을 수 있어야 하고,
# 공개 경로 검증이 실패했을 때는 Actions가 이 스크립트 없이 롤백을 부른다.
record_rollback_point() {
    mkdir -p "$BACKUP_DIR"
    cat > "$MANIFEST" <<MANIFEST
PREV_COMMIT=$PREV_COMMIT
DB_PATH=$DB_PATH
BACKUP_DIR=$BACKUP_DIR
BACKUP_STAMP=${1:-}
MANIFEST
}

echo "== 1. 배포 전 상태 기록 =="
PREV_COMMIT="$(git rev-parse HEAD)"
echo "현재 커밋: $PREV_COMMIT"
systemctl is-active --quiet "$SERVICE" && echo "서비스: active" || echo "서비스: inactive"
df -h "$REPO_DIR" | tail -1
record_rollback_point
ROLLBACK_ARMED=1

echo "== 2. 코드 동기화 =="
git fetch --all --tags
git checkout --detach "$TARGET"
# /health가 무엇이 돌고 있는지 답할 수 있어야 한다. data/는 gitignore라 checkout이
# 건드리지 않고, 최초 배포에는 아직 없다. 롤백하면 rollback.sh가 되돌린 태그로 다시 쓴다.
mkdir -p "$(dirname "$RELEASE_FILE")"
printf 'APP_RELEASE=%s\n' "$TARGET" > "$RELEASE_FILE"

# unit 파일은 저장소가 SSOT라고 스스로 밝힌다. 배포가 덮지 않으면 그 말이 거짓이
# 되고, EnvironmentFile 한 줄이 Pi에 닿지 않아 /health가 계속 dev라고 답한다.
UNIT_DST="/etc/systemd/system/$SERVICE.service"
if ! cmp -s "$REPO_DIR/deploy/$SERVICE.service" "$UNIT_DST"; then
    sudo cp "$REPO_DIR/deploy/$SERVICE.service" "$UNIT_DST"
    sudo systemctl daemon-reload
    echo "systemd unit 갱신 + daemon-reload"
fi
# --extra pi: spidev·gpiozero는 Pi에만 설치한다. 빼면 uv sync가 venv에서 지운다.
# --no-dev: alembic은 런타임 의존이라 마이그레이션에 필요한 것은 다 들어온다.
uv sync --frozen --no-dev --extra pi   # lock 불일치면 여기서 멈춘다. 강제로 넘기지 않는다.

echo "== 3. 서비스 중지 + DB 백업 =="
sudo systemctl stop "$SERVICE" || true
mkdir -p "$BACKUP_DIR"
if [ -f "$DB_PATH" ]; then
    for suffix in "" "-wal" "-shm"; do
        [ -f "${DB_PATH}${suffix}" ] && cp "${DB_PATH}${suffix}" "$BACKUP_DIR/$(basename "$DB_PATH")${suffix}.$STAMP"
    done
    BACKUP_FILE="$BACKUP_DIR/$(basename "$DB_PATH").$STAMP"
    # 확인 없는 백업은 백업이 아니다.
    [ -s "$BACKUP_FILE" ] || { echo "백업 실패: $BACKUP_FILE 가 비었다"; exit 1; }
    echo "백업 완료: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"
    record_rollback_point "$STAMP"
else
    echo "DB 파일 없음 — 최초 배포로 간주"
fi

echo "== 4. 마이그레이션 =="
uv run alembic current
uv run alembic upgrade head

echo "== 5. 기동 =="
sudo systemctl start "$SERVICE"

echo "== 6. 헬스체크 =="
# 경로에 버전 prefix가 없다 — 앱 계약과 같은 경로를 친다 (main.py의 라우터 등록).
# 기동은 Pi Zero 2W에서 10초 가까이 걸린다. 고정 대기는 느린 날 거짓 실패를 만들고
# 빠른 날 시간을 버린다. 응답을 조건으로 기다리되 상한을 둔다.
READY_TIMEOUT_S=90
DEADLINE=$((SECONDS + READY_TIMEOUT_S))
until curl -fsS http://localhost:8000/health 2>/dev/null | grep -q '"status"'; do
    systemctl is-active --quiet "$SERVICE" || {
        echo "기동 실패"; journalctl -u "$SERVICE" -n 50 --no-pager; exit 1
    }
    if [ "$SECONDS" -ge "$DEADLINE" ]; then
        echo "헬스체크 실패 — ${READY_TIMEOUT_S}초 안에 응답이 없다"
        journalctl -u "$SERVICE" -n 50 --no-pager
        exit 1
    fi
    sleep 2
done
curl -fsS http://localhost:8000/health

echo "== 7. 실측 기록 =="
PID="$(systemctl show -p MainPID --value "$SERVICE")"
echo "RSS: $(ps -o rss= -p "$PID" | tr -d ' ') KB"
journalctl -u "$SERVICE" -n 20 --no-pager

cat <<EOF

배포 완료.
  이전 커밋: $PREV_COMMIT
  현재 커밋: $(git rev-parse HEAD)
  백업:      $BACKUP_DIR/*.$STAMP

이 배포가 실패했다면 롤백은 이미 자동으로 돌았다.
배포 후에 문제를 발견한 경우에만 직접 부른다:
  ./deploy/rollback.sh
EOF
