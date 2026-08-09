"""식별자·토큰 생성. 앱 등록 경로의 계약이자 인증의 뿌리다."""

from __future__ import annotations

import hashlib

import pytest

from app.core.identity import (
    default_label,
    hash_token,
    new_device_token,
    new_public_id,
    normalize_mac,
)
from app.domain.exceptions import InvalidMac

_CANONICAL = "AA:BB:CC:DD:EE:FF"


class TestNormalizeMac:
    @pytest.mark.parametrize(
        "raw",
        [
            "AA:BB:CC:DD:EE:FF",
            "aa:bb:cc:dd:ee:ff",
            "AA-BB-CC-DD-EE-FF",
            "AABBCCDDEEFF",
            "aabbccddeeff",
            " aa bb cc dd ee ff ",
        ],
    )
    def test_separator_and_case_are_normalised(self, raw: str) -> None:
        """앱(services/deviceRegistry.ts)과 같은 형식으로 수렴해야 한다."""
        assert normalize_mac(raw) == _CANONICAL

    def test_result_is_upper_case_with_colons(self) -> None:
        result = normalize_mac("aabbccddeeff")

        assert result.count(":") == 5
        assert result == result.upper()
        assert len(result) == 17

    @pytest.mark.parametrize(
        "raw",
        [
            "",
            "AA:BB:CC:DD:EE",  # 5옥텟
            "AA:BB:CC:DD:EE:FF:00",  # 7옥텟
            "AABBCCDDEEF",  # 11자
            "AABBCCDDEEFFF",  # 13자
            "ZZ:BB:CC:DD:EE:FF",  # hex 아님
            "사람이 읽는 라벨",
        ],
    )
    def test_non_mac_input_is_rejected(self, raw: str) -> None:
        with pytest.raises(InvalidMac):
            normalize_mac(raw)

    def test_is_idempotent(self) -> None:
        assert normalize_mac(normalize_mac(_CANONICAL)) == _CANONICAL


class TestHashToken:
    def test_is_sha256_hex(self) -> None:
        assert hash_token("dtk_abc") == hashlib.sha256(b"dtk_abc").hexdigest()

    def test_is_deterministic(self) -> None:
        assert hash_token("dtk_abc") == hash_token("dtk_abc")

    def test_different_tokens_hash_differently(self) -> None:
        assert hash_token("dtk_abc") != hash_token("dtk_abd")

    def test_does_not_contain_the_original(self) -> None:
        """원문은 저장되지 않는다 (db-schema.md D9)."""
        assert "dtk_abc" not in hash_token("dtk_abc")


class TestGeneratedIdentifiers:
    def test_device_token_carries_its_prefix(self) -> None:
        assert new_device_token().startswith("dtk_")

    def test_public_id_carries_its_prefix(self) -> None:
        assert new_public_id().startswith("dev_")

    def test_identifiers_are_not_sequential(self) -> None:
        """/devices/1 순회를 막는 것이 public_id의 존재 이유다 (D8)."""
        generated = {new_public_id() for _ in range(200)}

        assert len(generated) == 200

    def test_tokens_are_not_reused(self) -> None:
        assert len({new_device_token() for _ in range(200)}) == 200

    def test_token_has_enough_entropy_to_resist_guessing(self) -> None:
        assert len(new_device_token()) > 24


class TestDefaultLabel:
    def test_uses_the_mac_tail_so_devices_are_distinguishable(self) -> None:
        assert default_label(_CANONICAL) == "킥보드 EEFF"

    def test_differs_between_devices(self) -> None:
        assert default_label(_CANONICAL) != default_label("AA:BB:CC:DD:11:22")
