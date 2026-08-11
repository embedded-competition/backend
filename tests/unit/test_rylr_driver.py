"""RYLR 초기화·수신 절차.

전파 파라미터가 노드와 하나라도 어긋나면 수신이 0이 된다. 그런데 0은 에러가
아니라 침묵이라 원인을 되짚기 어렵다 — 그래서 초기화가 무엇을 보냈는지와
모듈이 거절했는지를 테스트로 못박는다.
"""

from __future__ import annotations

import pytest

from app.infrastructure.lora.rylr import RylrConfig, RylrDriver, RylrNotResponding
from app.infrastructure.lora.rylr.driver import RylrRejectedCommand


class FakeAtPort:
    def __init__(self, replies: list[str | None]) -> None:
        self.written: list[str] = []
        self._replies = replies
        self.closed = False

    def write_line(self, line: str) -> None:
        self.written.append(line)

    def read_line(self, timeout_s: float) -> str | None:
        return self._replies.pop(0) if self._replies else None

    def close(self) -> None:
        self.closed = True


def _config(**overrides: object) -> RylrConfig:
    defaults: dict[str, object] = {
        "port": "/dev/ttyAMA0",
        "baud": 115_200,
        "address": 1,
        "network_id": 18,
        "frequency_hz": 922_000_000,
        "spreading_factor": 7,
        "bandwidth_hz": 125_000,
        "coding_rate": 5,
        "preamble_length": 8,
    }
    return RylrConfig(**{**defaults, **overrides})  # type: ignore[arg-type]


class TestStartReceiving:
    def test_sends_every_setting(self) -> None:
        port = FakeAtPort(["+VER=RYLR998_1.2.3", "+OK", "+OK", "+OK", "+OK"])

        version = RylrDriver(port, _config()).start_receiving()

        assert version == "+VER=RYLR998_1.2.3"
        assert port.written == [
            "AT+VER?",
            "AT+ADDRESS=1",
            "AT+NETWORKID=18",
            "AT+BAND=922000000",
            "AT+PARAMETER=7,7,1,8",
        ]

    def test_silence_names_what_to_check(self) -> None:
        """무응답은 배선·전원·보율 셋 중 하나다. 그 셋을 메시지가 말해야 한다."""
        port = FakeAtPort([])

        with pytest.raises(RylrNotResponding, match="TX↔RX"):
            RylrDriver(port, _config()).start_receiving()

    def test_rejected_command_stops_startup(self) -> None:
        port = FakeAtPort(["+VER=X", "+ERR=12"])

        with pytest.raises(RylrRejectedCommand, match="AT\\+ADDRESS=1"):
            RylrDriver(port, _config()).start_receiving()


class TestConfigTranslation:
    def test_coding_rate_maps_to_module_numbering(self) -> None:
        """서버는 4/5를 5로 적고 RYLR은 1로 받는다."""
        assert _config(coding_rate=5).coding_rate_code == 1
        assert _config(coding_rate=8).coding_rate_code == 4

    @pytest.mark.parametrize(("hz", "code"), [(125_000, 7), (250_000, 8), (500_000, 9)])
    def test_bandwidth_maps_to_code(self, hz: int, code: int) -> None:
        assert _config(bandwidth_hz=hz).bandwidth_code == code

    def test_unsupported_bandwidth_is_named(self) -> None:
        with pytest.raises(ValueError, match="지원하지 않는 대역폭"):
            _ = _config(bandwidth_hz=62_500).bandwidth_code


class TestPoll:
    def test_returns_frame_on_receive(self) -> None:
        port = FakeAtPort(["+RCV=1,4,DEAD,-70,7"])

        packet = RylrDriver(port, _config()).poll()

        assert packet is not None
        assert packet.payload == bytes.fromhex("DEAD")

    def test_silence_is_not_a_frame(self) -> None:
        assert RylrDriver(FakeAtPort([]), _config()).poll() is None

    def test_unrelated_line_is_ignored(self) -> None:
        """설정 응답이 늦게 도착해도 프레임으로 오해하면 안 된다."""
        assert RylrDriver(FakeAtPort(["+OK"]), _config()).poll() is None
