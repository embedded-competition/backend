"""RYLR `+RCV` 응답 파싱.

RYLR은 수신 결과를 콤마로 나눈 한 줄로 준다. 페이로드 안에도 콤마가 들어갈 수
있으므로 길이 필드를 믿고 잘라야 한다 — 콤마로 split하면 프레임이 깨진다.
"""

from __future__ import annotations

import pytest

from app.domain.exceptions import FrameError
from app.infrastructure.lora.rylr import parse_packet


class TestHexPayload:
    def test_fields_are_read(self) -> None:
        packet = parse_packet("+RCV=50,8,DEADBEEF,-99,40", "hex")

        assert packet.address == 50
        assert packet.payload == bytes.fromhex("DEADBEEF")
        assert (packet.rssi, packet.snr) == (-99, 40.0)

    def test_length_counts_characters_not_bytes(self) -> None:
        """길이 필드는 모듈이 센 문자 수다. hex면 바이트 수의 두 배가 된다."""
        packet = parse_packet("+RCV=1,8,0011AABB,-70,7", "hex")

        assert packet.payload == bytes.fromhex("0011AABB")

    def test_non_hex_payload_is_rejected(self) -> None:
        with pytest.raises(FrameError):
            parse_packet("+RCV=1,5,HELLO,-70,7", "hex")


class TestTextPayload:
    def test_payload_stays_raw(self) -> None:
        packet = parse_packet("+RCV=1,5,HELLO,-70,7", "text")

        assert packet.payload == b"HELLO"

    def test_comma_inside_payload_survives(self) -> None:
        """콤마로 split하면 여기서 깨진다. 길이 필드로 잘라야 한다."""
        packet = parse_packet("+RCV=1,7,A,B,C,D,-70,7", "text")

        assert packet.payload == b"A,B,C,D"
        assert (packet.rssi, packet.snr) == (-70, 7.0)


class TestMalformed:
    @pytest.mark.parametrize(
        "line",
        [
            "+RCV=abc,4,DEAD,-70,7",
            "+RCV=1,4",
            "+RCV=1,99,DEAD,-70,7",
            "+RCV=1,4,DEAD,-70",
        ],
    )
    def test_is_rejected(self, line: str) -> None:
        with pytest.raises(FrameError):
            parse_packet(line, "hex")

    def test_unreadable_radio_quality_does_not_lose_the_frame(self) -> None:
        """RSSI가 깨져도 페이로드는 살린다 — 전파 품질은 부가 정보다."""
        packet = parse_packet("+RCV=1,4,DEAD,x,y", "hex")

        assert packet.payload == bytes.fromhex("DEAD")
        assert (packet.rssi, packet.snr) == (None, None)
