"""SX1276 드라이버 단위 테스트. 실제 SPI·GPIO 없이 초기화 순서를 고정한다."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from app.infrastructure.lora import registers as reg
from app.infrastructure.lora.radio import Sx1276Driver
from app.infrastructure.lora.registers import RadioConfig

CONFIG = RadioConfig(
    spi_bus=0,
    spi_device=0,
    reset_gpio=22,
    frequency_hz=922_000_000,
    spreading_factor=7,
    bandwidth_hz=125_000,
    coding_rate=5,
    preamble_length=8,
    sync_word=0x12,
)


@dataclass
class FakeBus:
    """레지스터 접근을 순서대로 기록한다. 값은 칩이 살아 있는 상태를 흉내낸다."""

    values: dict[int, int] = field(default_factory=lambda: {reg.VERSION: reg.EXPECTED_CHIP_VERSION})
    log: list[str] = field(default_factory=list)
    writes: dict[int, int] = field(default_factory=dict)

    def read(self, register: int) -> int:
        self.log.append(f"read:{register:#04x}")
        return self.values.get(register, 0)

    def write(self, register: int, value: int) -> None:
        self.log.append(f"write:{register:#04x}")
        self.writes[register] = value

    def close(self) -> None:
        self.log.append("bus-close")


@dataclass
class FakeResetPin:
    log: list[str] = field(default_factory=list)

    def pulse(self) -> None:
        self.log.append("reset")

    def close(self) -> None:
        self.log.append("pin-close")


def _driver(bus: FakeBus, pin: FakeResetPin) -> Sx1276Driver:
    return Sx1276Driver(bus=bus, config=CONFIG, reset=pin)


class TestStartup:
    def test_resets_before_touching_registers(self) -> None:
        """칩이 이상 상태로 남아 있으면 모드 전환이 먹지 않는다 — 리셋이 먼저다."""
        bus, pin = FakeBus(), FakeResetPin()
        shared: list[str] = []
        bus.log = pin.log = shared

        _driver(bus, pin).start_receiving()

        assert shared[0] == "reset"
        assert shared[1] == f"read:{reg.VERSION:#04x}"

    def test_wrong_chip_version_fails_loudly(self) -> None:
        bus = FakeBus(values={reg.VERSION: 0x00})

        with pytest.raises(RuntimeError, match="배선"):
            _driver(bus, FakeResetPin()).start_receiving()

    def test_ends_in_continuous_receive_mode(self) -> None:
        bus = FakeBus()

        _driver(bus, FakeResetPin()).start_receiving()

        assert bus.writes[reg.OP_MODE] == reg.LONG_RANGE_MODE | reg.MODE_RX_CONTINUOUS
        assert bus.writes[reg.SYNC_WORD] == CONFIG.sync_word


class TestPoll:
    def test_no_irq_yields_nothing(self) -> None:
        assert _driver(FakeBus(), FakeResetPin()).poll() is None

    def test_radio_crc_error_is_dropped(self) -> None:
        """라디오 레벨 CRC는 프레임 CRC와 다른 계층이다 — 여기서 버린다."""
        bus = FakeBus(values={reg.IRQ_FLAGS: reg.IRQ_RX_DONE | reg.IRQ_PAYLOAD_CRC_ERROR})

        assert _driver(bus, FakeResetPin()).poll() is None

    def test_received_payload_carries_radio_quality(self) -> None:
        bus = FakeBus(
            values={
                reg.IRQ_FLAGS: reg.IRQ_RX_DONE,
                reg.RX_NB_BYTES: 2,
                reg.FIFO: 0xAB,
                reg.PKT_RSSI: 83,
                reg.PKT_SNR: 30,
            }
        )

        frame = _driver(bus, FakeResetPin()).poll()

        assert frame is not None
        assert frame.payload == bytes([0xAB, 0xAB])
        assert frame.rssi == 83 - 157
        assert frame.snr == pytest.approx(7.5)


class TestStop:
    def test_releases_both_bus_and_pin(self) -> None:
        """핀을 안 놓으면 다음 기동이 GPIO 점유 오류로 죽는다."""
        bus, pin = FakeBus(), FakeResetPin()

        _driver(bus, pin).stop()

        assert "bus-close" in bus.log
        assert "pin-close" in pin.log
