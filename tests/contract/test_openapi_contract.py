"""스펙에서 생성한 요청을 전 endpoint에 흘려보낸다."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import hypothesis
import pytest
import schemathesis
from alembic import command
from alembic.config import Config

from app.core.config import Settings
from app.main import create_app

pytestmark = pytest.mark.contract

_WORKSPACE = Path(tempfile.mkdtemp(prefix="orca-contract-"))
_SETTINGS = Settings(
    environment="local",
    database_path=_WORKSPACE / "contract.db",
    lora_enabled=False,
    lora_source="fake",
    push_delivery="log",
)
_APP = create_app(_SETTINGS)

schema = schemathesis.openapi.from_asgi("/openapi.json", _APP)

# 앱이 소유하지 않는 응답. FastAPI 기본 핸들러가 만드는 라우팅 404·405이며
# 도메인 에러 계약의 대상이 아니다.
_FRAMEWORK_KEYS = {"detail"}


@pytest.fixture(scope="module", autouse=True)
def _migrated_db() -> None:
    """스키마만 만든다. 나머지는 lifespan이 _SETTINGS 그대로 연다."""
    alembic_config = Config("alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", _SETTINGS.database_url)
    command.upgrade(alembic_config, "head")


@schemathesis.check
def single_error_shape(ctx: Any, response: Any, case: Any) -> None:
    """에러 응답 형식은 전 endpoint 동일하다 (api-spec.md §공통 에러).

    앱이 `error` 키 하나로 분기하므로, endpoint 하나만 형식이 달라도 그 화면이
    조용히 깨진다. endpoint별 테스트로는 "전부 같은가"를 증명할 수 없다.
    """
    if response.status_code < 400:
        return
    payload = response.json()
    if isinstance(payload, dict) and set(payload) <= _FRAMEWORK_KEYS:
        return
    assert set(payload) == {"error", "requestId"}, (
        f"{case.method} {case.path} → {response.status_code} 형식 이탈: {payload}"
    )


# 경로 파라미터가 제약 없는 문자열이라 생성값의 상당수가 걸러진다. 이는 API의
# 결함이 아니라 생성기의 성질이고, 억제하지 않으면 시드에 따라 무작위로 실패한다
# (pytest-randomly가 매 실행 시드를 바꾼다). 배포 게이트가 비결정적이면 게이트가 아니다.
#
# 예제마다 lifespan이 한 번씩 돌아 예제 단가가 크다. 느린 러너에서 시간 기반
# 판정이 걸리는 것도 같은 이유로 막는다.
@schema.parametrize()
@hypothesis.settings(
    suppress_health_check=[
        hypothesis.HealthCheck.filter_too_much,
        hypothesis.HealthCheck.too_slow,
    ],
    deadline=None,
)
def test_contract(case: Any) -> None:
    case.call_and_validate(checks=[schemathesis.checks.not_a_server_error, single_error_shape])
