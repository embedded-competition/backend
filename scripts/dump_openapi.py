"""OpenAPI 명세를 파일로 덤프한다.

앱 클라이언트(별도 repo)와의 계약 공유 수단. API 변경 PR은 재생성한
openapi.json diff를 포함한다 — diff가 비면 계약 변경 없음이 증명된다.

    uv run python scripts/dump_openapi.py
"""

from __future__ import annotations

import json
from pathlib import Path

from app.core.config import Settings
from app.main import create_app

OUTPUT = Path("docs/openapi.json")

_CONTRACT_SETTINGS = Settings(lora_enabled=False)
"""스펙이 이 기계의 .env나 꽂힌 하드웨어를 따라 흔들리지 않게 못 박는다.

수신을 끄는 것은 그 목적뿐이다 — 노출되는 경로는 설정과 무관하다.
"""


def main() -> None:
    app = create_app(_CONTRACT_SETTINGS)
    spec = app.openapi()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    paths = len(spec.get("paths", {}))
    print(f"wrote {OUTPUT} ({paths} paths)")


if __name__ == "__main__":
    main()
