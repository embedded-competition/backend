"""규칙이 겨냥하는 경로. 다른 프로젝트에 옮길 때 **이 파일만** 고친다."""

from __future__ import annotations

from pathlib import Path
from typing import Final

ROOT: Final = Path(__file__).resolve().parents[2] / "app"

DOMAIN: Final = ROOT / "domain"
CORE: Final = ROOT / "core"
API: Final = ROOT / "api"
RUNTIME: Final = ROOT / "runtime"
INFRASTRUCTURE: Final = ROOT / "infrastructure"

LAYERS: Final = (DOMAIN, CORE, API, RUNTIME, INFRASTRUCTURE)

# --- 규칙별 예외. 이유를 여기 적는다 -------------------------------------

# 환경변수를 읽어도 되는 유일한 지점. Settings가 설정 SSOT다.
CONFIG_MODULE: Final = CORE / "config.py"

# 트랜잭션을 여닫는 유일한 지점. 요청 스코프와 수신 task 스코프 둘뿐이다.
TRANSACTION_SCOPES: Final = (RUNTIME / "deps.py", RUNTIME / "wiring.py")

# ORM 매핑 선언 전용 모듈. 여기 클래스에 도메인 메서드가 붙으면 계층 누수다.
ORM_MODULE: Final = INFRASTRUCTURE / "db" / "orm.py"

# 시각을 실제로 읽는 어댑터. Clock port의 유일한 시스템 구현이다.
CLOCK_ADAPTER: Final = INFRASTRUCTURE / "clock.py"
