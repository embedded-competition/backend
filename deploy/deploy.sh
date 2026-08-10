#!/usr/bin/env bash
# Raspberry Pi 배포. 절차는 workflows/backend/deploy-rpi.md.
#
#   ./deploy/deploy.sh <target-commit-or-tag>
#
# 문서에만 적힌 수동 명령 나열을 만들지 않기 위해 스크립트가 SSOT다.
set -euo pipefail

TARGET="${1:?배포할 커밋 또는 태그를 지정해야 한다}"
SERVICE=orca-backend
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DB_PATH="${APP_DATABASE_PATH:-$REPO_DIR/data/orca.db}"
BACKUP_DIR="$REPO_DIR/data/backups"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"

cd "$REPO_DIR"

echo "== 1. 배포 전 상태 기록 =="
PREV_COMMIT="$(git rev-parse HEAD)"
echo "현재 커밋: $PREV_COMMIT"
systemctl is-active --quiet "$SERVICE" && echo "서비스: active" || echo "서비스: inactive"
df -h "$REPO_DIR" | tail -1

echo "== 2. 코드 동기화 =="
git fetch --all --tags
git checkout --detach "$TARGET"
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
else
    echo "DB 파일 없음 — 최초 배포로 간주"
fi

echo "== 4. 마이그레이션 =="
uv run alembic current
uv run alembic upgrade head

echo "== 5. 기동 =="
sudo systemctl start "$SERVICE"
sleep 3
systemctl is-active --quiet "$SERVICE" || { echo "기동 실패"; journalctl -u "$SERVICE" -n 50 --no-pager; exit 1; }

echo "== 6. 헬스체크 =="
# 경로에 버전 prefix가 없다 — 앱 계약과 같은 경로를 친다 (main.py의 라우터 등록).
curl -fsS http://localhost:8000/health | tee /dev/stderr | grep -q '"status"' || {
    echo "헬스체크 실패"; exit 1;
}

echo "== 7. 실측 기록 =="
PID="$(systemctl show -p MainPID --value "$SERVICE")"
echo "RSS: $(ps -o rss= -p "$PID" | tr -d ' ') KB"
journalctl -u "$SERVICE" -n 20 --no-pager

cat <<EOF

배포 완료.
  이전 커밋: $PREV_COMMIT
  현재 커밋: $(git rev-parse HEAD)
  백업:      $BACKUP_DIR/*.$STAMP

롤백이 필요하면:
  sudo systemctl stop $SERVICE
  git checkout --detach $PREV_COMMIT && uv sync --frozen --extra pi
  cp $BACKUP_DIR/\$(basename "$DB_PATH").$STAMP $DB_PATH
  sudo systemctl start $SERVICE
EOF
