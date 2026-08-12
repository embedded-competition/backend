#!/usr/bin/env bash
# 배포 실패 시 직전 상태로 되돌린다.
#
#   ./deploy/rollback.sh
#
# deploy.sh가 남긴 data/backups/last-deploy.env를 읽는다. deploy.sh가 실패하면
# 스스로 이 스크립트를 부르고, deploy.sh가 성공한 뒤 공개 경로 검증이 실패하면
# Actions가 부른다. 되돌릴 지점을 모르면 아무것도 하지 않고 멈춘다.
set -Eeuo pipefail

# 비대화형 SSH는 로그인 프로필을 읽지 않는다 (deploy.sh와 같은 전제).
PATH="$HOME/.local/bin:$PATH"
export PATH

REPO_DIR="${DEPLOY_REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"

# 아래 checkout이 이 파일 자체를 갈아치운다 (deploy.sh와 같은 이유).
if [ -z "${ROLLBACK_DETACHED:-}" ]; then
    _copy="$(mktemp)"
    cat "${BASH_SOURCE[0]}" > "$_copy"
    ROLLBACK_DETACHED="$_copy" DEPLOY_REPO_DIR="$REPO_DIR" exec bash "$_copy" "$@"
fi
trap 'rm -f "$ROLLBACK_DETACHED"' EXIT

SERVICE=orca-backend
MANIFEST="$REPO_DIR/data/backups/last-deploy.env"

cd "$REPO_DIR"

[ -f "$MANIFEST" ] || { echo "되돌릴 지점을 모른다 — $MANIFEST 가 없다"; exit 1; }
# shellcheck source=/dev/null
. "$MANIFEST"
: "${PREV_COMMIT:?manifest에 PREV_COMMIT이 없다}"

echo "== 되돌릴 지점 =="
echo "커밋: $PREV_COMMIT"
echo "백업: ${BACKUP_STAMP:-없음}"

echo "== 1. 서비스 중지 =="
sudo systemctl stop "$SERVICE" || true

echo "== 2. 코드 되감기 =="
git checkout --detach "$PREV_COMMIT"
# 되돌린 뒤에도 /health가 실패한 태그를 말하면 롤백됐는지 알 수 없다.
printf 'APP_RELEASE=%s\n' "$PREV_COMMIT" > "$REPO_DIR/data/release.env"
uv sync --frozen --no-dev --extra pi

echo "== 3. DB 복원 =="
if [ -n "${BACKUP_STAMP:-}" ]; then
    for suffix in "" "-wal" "-shm"; do
        source_file="$BACKUP_DIR/$(basename "$DB_PATH")${suffix}.$BACKUP_STAMP"
        if [ -f "$source_file" ]; then
            cp "$source_file" "${DB_PATH}${suffix}"
        else
            # 백업 시점에 없던 파일은 지금도 없어야 한다. 남겨 두면 복원한 .db와
            # 짝이 맞지 않는 WAL이 붙는다.
            rm -f "${DB_PATH}${suffix}"
        fi
    done
    echo "복원 완료 — 백업 시점 이후 수신한 프레임은 유실됐다"
else
    echo "백업 없음 — 코드만 되감는다 (백업 전에 실패한 경우)"
fi

echo "== 4. 기동 =="
sudo systemctl start "$SERVICE"

READY_TIMEOUT_S=90
DEADLINE=$((SECONDS + READY_TIMEOUT_S))
until curl -fsS http://localhost:8000/health 2>/dev/null | grep -q '"status"'; do
    if [ "$SECONDS" -ge "$DEADLINE" ]; then
        echo "롤백 후에도 기동하지 못했다 — 수동 개입이 필요하다"
        journalctl -u "$SERVICE" -n 50 --no-pager
        exit 1
    fi
    sleep 2
done

echo
echo "롤백 완료. 현재 커밋: $(git rev-parse --short HEAD)"
curl -fsS http://localhost:8000/health
