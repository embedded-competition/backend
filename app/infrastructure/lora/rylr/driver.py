from __future__ import annotations

import logging
from dataclasses import dataclass

from app.infrastructure.lora.rylr.at_port import AtPort
from app.infrastructure.lora.rylr.config import RylrConfig
from app.infrastructure.lora.rylr.packet import RECEIVE_PREFIX, ReceivedPacket, parse_packet

logger = logging.getLogger(__name__)

_OK = "+OK"
_ERROR = "+ERR="
_VERSION_QUERY = "AT+VER?"


class RylrNotResponding(RuntimeError):
    pass


class RylrRejectedCommand(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class RylrDriver:
    port: AtPort
    config: RylrConfig

    def start_receiving(self) -> str:
        version = self._ask(_VERSION_QUERY)
        for command in self._setup_commands():
            self._ask(command)
        return version

    def poll(self) -> ReceivedPacket | None:
        line = self.port.read_line(self.config.read_timeout_s)
        if line is None:
            return None
        if not line.startswith(RECEIVE_PREFIX):
            logger.debug("rylr line ignored", extra={"line": line})
            return None
        return parse_packet(line, self.config.payload)

    def close(self) -> None:
        self.port.close()

    def _setup_commands(self) -> tuple[str, ...]:
        return (
            f"AT+ADDRESS={self.config.address}",
            f"AT+NETWORKID={self.config.network_id}",
            f"AT+BAND={self.config.frequency_hz}",
            self.config.parameter_command,
        )

    def _ask(self, command: str) -> str:
        self.port.write_line(command)
        line = self._await_reply(command)
        if line.startswith(_ERROR):
            raise RylrRejectedCommand(f"{command} 거부됨: {line}")
        return line

    def _await_reply(self, command: str) -> str:
        while True:
            line = self.port.read_line(self.config.command_timeout_s)
            if line is None:
                raise RylrNotResponding(
                    f"{command}에 응답이 없다 — 배선(TX↔RX 교차)·전원(3.3V)·보율을 확인하라"
                )
            if line.startswith((_OK, _ERROR, "+")) and not line.startswith(RECEIVE_PREFIX):
                return line
