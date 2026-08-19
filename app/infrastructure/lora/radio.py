from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime

from app.domain.ports.frame_source import RawFrame
from app.infrastructure.lora import registers as reg
from app.infrastructure.lora.gpio import GpioResetPin, ResetPin
from app.infrastructure.lora.registers import RadioConfig
from app.infrastructure.lora.spi import RegisterBus, SpiRegisterBus

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Sx1276Driver:
    bus: RegisterBus
    config: RadioConfig
    reset: ResetPin

    def start_receiving(self) -> int:
        self.reset.pulse()
        version = self.bus.read(reg.VERSION)
        if version != reg.EXPECTED_CHIP_VERSION:
            raise RuntimeError(f"SX1276이 응답하지 않는다 (version={version:#04x}). 배선·전원 확인")

        self.bus.write(reg.OP_MODE, reg.LONG_RANGE_MODE | reg.MODE_SLEEP)
        msb, mid, lsb = reg.frequency_words(self.config.frequency_hz)
        self.bus.write(reg.FRF_MSB, msb)
        self.bus.write(reg.FRF_MSB + 1, mid)
        self.bus.write(reg.FRF_MSB + 2, lsb)
        self.bus.write(reg.MODEM_CONFIG1, reg.modem_config1(self.config))
        self.bus.write(reg.MODEM_CONFIG2, reg.modem_config2(self.config))
        self.bus.write(reg.PREAMBLE_MSB, self.config.preamble_length >> 8)
        self.bus.write(reg.PREAMBLE_LSB, self.config.preamble_length & 0xFF)
        self.bus.write(reg.SYNC_WORD, self.config.sync_word)
        self.bus.write(reg.OP_MODE, reg.LONG_RANGE_MODE | reg.MODE_RX_CONTINUOUS)
        return version

    def poll(self) -> RawFrame | None:
        irq = self.bus.read(reg.IRQ_FLAGS)
        if not irq & reg.IRQ_RX_DONE:
            return None
        self.bus.write(reg.IRQ_FLAGS, 0xFF)

        if irq & reg.IRQ_PAYLOAD_CRC_ERROR:
            logger.warning("lora radio crc error")
            return None

        length = self.bus.read(reg.RX_NB_BYTES)
        self.bus.write(reg.FIFO_ADDR_PTR, self.bus.read(reg.FIFO_RX_CURRENT))
        payload = bytes(self.bus.read(reg.FIFO) for _ in range(length))
        return RawFrame(
            payload=payload,
            received_at=datetime.now(UTC),
            rssi=reg.decode_rssi(self.bus.read(reg.PKT_RSSI)),
            snr=reg.decode_snr(self.bus.read(reg.PKT_SNR)),
        )

    def stop(self) -> None:
        self.bus.write(reg.OP_MODE, reg.LONG_RANGE_MODE | reg.MODE_STDBY)
        self.bus.close()
        self.reset.close()


class Sx1276FrameSource:
    def __init__(self, config: RadioConfig, driver: Sx1276Driver | None = None) -> None:
        self._config = config
        self._driver = driver
        self._closed = False

    async def frames(self) -> AsyncIterator[RawFrame]:
        driver = await asyncio.to_thread(self._ensure_driver)
        while not self._closed:
            frame = await asyncio.to_thread(driver.poll)
            if frame is not None:
                yield frame
            else:
                await asyncio.sleep(self._config.poll_interval_s)

    async def close(self) -> None:
        self._closed = True
        if self._driver is not None:
            await asyncio.to_thread(self._driver.stop)
            self._driver = None

    def _ensure_driver(self) -> Sx1276Driver:
        if self._driver is None:
            self._driver = Sx1276Driver(
                bus=SpiRegisterBus(self._config.spi_bus, self._config.spi_device),
                config=self._config,
                reset=GpioResetPin(self._config.reset_gpio),
            )
        version = self._driver.start_receiving()
        logger.info(
            "sx1276 ready",
            extra={
                "chip_version": hex(version),
                "frequency_hz": self._config.frequency_hz,
                "spreading_factor": self._config.spreading_factor,
            },
        )
        return self._driver
