"""SX1276 칩 드라이버 + FrameSource 구현.

레지스터 맵은 registers.py, SPI 접근은 spi.py가 소유한다. 이 파일은 "칩을 어떻게
초기화하고 프레임을 어떻게 꺼내는가"만 안다 — 파싱·저장·판단은 하지 않는다.
"""

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
    """동기 칩 제어. 호출자가 스레드로 넘긴다."""

    bus: RegisterBus
    config: RadioConfig
    reset: ResetPin

    def start_receiving(self) -> int:
        """초기화 후 칩 version을 반환한다. 배선 문제를 여기서 잡는다.

        레지스터를 쓰기 전에 하드웨어 리셋을 건다 — 칩이 이상 상태로 남아 있으면
        모드 전환이 먹지 않아 재부팅해도 수신이 0인 채로 돈다.
        """
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
        """수신 완료 IRQ가 없으면 None. 호출자가 간격을 정한다."""
        irq = self.bus.read(reg.IRQ_FLAGS)
        if not irq & reg.IRQ_RX_DONE:
            return None
        self.bus.write(reg.IRQ_FLAGS, 0xFF)

        if irq & reg.IRQ_PAYLOAD_CRC_ERROR:
            # 라디오 레벨 CRC. 프레임 CRC와 별개 계층이라 여기서 버린다.
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
    """드라이버를 asyncio 경계로 감싼다.

    DIO0 인터럽트가 아니라 IRQ 레지스터 폴링을 쓴다 — GPIO 콜백은 다른 스레드에서
    실행돼 asyncio로 넘기는 경로가 복잡하다. 50ms 폴링이면 LoRa 프레임 간격
    (수 초~수 분) 대비 충분히 촘촘하다.
    """

    def __init__(self, config: RadioConfig, driver: Sx1276Driver | None = None) -> None:
        self._config = config
        self._driver = driver
        self._closed = False

    async def frames(self) -> AsyncIterator[RawFrame]:
        driver = await asyncio.to_thread(self._ensure_driver)
        while not self._closed:
            # blocking SPI 읽기를 이벤트 루프에서 직접 호출하지 않는다.
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
