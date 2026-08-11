from __future__ import annotations

from typing import Any


class SerialAtPort:
    def __init__(self, port: str, baud: int) -> None:
        import serial

        self._serial: Any = serial.Serial(port=port, baudrate=baud, timeout=1.0)

    def write_line(self, line: str) -> None:
        self._serial.write(f"{line}\r\n".encode())
        self._serial.flush()

    def read_line(self, timeout_s: float) -> str | None:
        self._serial.timeout = timeout_s
        raw = self._serial.readline()
        if not raw:
            return None
        line = raw.decode("utf-8", "replace").strip()
        return line or None

    def close(self) -> None:
        self._serial.close()
