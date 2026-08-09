"""계층 규칙 실행. import 그래프 계약은 import-linter(pyproject.toml)가 담당한다."""

from __future__ import annotations

from tests.architecture import lint_target as target
from tests.architecture import rules
from tests.architecture.engine import assert_clean


class TestConfiguration:
    def test_clock_is_injected_in_domain_and_core(self) -> None:
        assert_clean(rules.forbid_direct_clock, [target.DOMAIN, target.CORE])

    def test_environment_is_read_only_in_settings(self) -> None:
        assert_clean(rules.forbid_direct_env, [target.ROOT])


class TestPersistence:
    def test_transaction_boundary_is_owned_by_session_scope(self) -> None:
        assert_clean(rules.forbid_manual_transaction, [target.ROOT])

    def test_no_legacy_query_api(self) -> None:
        assert_clean(rules.forbid_legacy_query_api, [target.ROOT])

    def test_orm_classes_carry_no_behaviour(self) -> None:
        assert_clean(rules.forbid_business_method_on_orm, [target.INFRASTRUCTURE])


class TestSchema:
    def test_no_pydantic_v1_api(self) -> None:
        assert_clean(rules.forbid_pydantic_v1_api, [target.ROOT])

    def test_domain_exceptions_do_not_know_http(self) -> None:
        assert_clean(rules.forbid_domain_status_code, [target.DOMAIN])


class TestStyle:
    def test_no_handwritten_storage_constructor(self) -> None:
        assert_clean(rules.forbid_handwritten_init, [target.ROOT])
