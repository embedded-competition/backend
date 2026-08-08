"""OpenAPI 명세를 파일로 덤프한다.

앱 클라이언트(별도 repo)와의 계약 공유 수단. API 변경 PR은 재생성한
openapi.json diff를 포함한다 — diff가 비면 계약 변경 없음이 증명된다.

    uv run python scripts/dump_openapi.py
"""

from __future__ import annotations

import json
from pathlib import Path

from app.main import create_app

OUTPUT = Path("docs/openapi.json")


def main() -> None:
    app = create_app()
    spec = app.openapi()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths = len(spec.get("paths", {}))
    print(f"wrote {OUTPUT} ({paths} paths)")


if __name__ == "__main__":
    main()
