from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime

from app.domain.ports.frame_source import RawFrame
from app.infrastructure.lora.rylr.config import RylrConfig
from app.infrastructure.lora.rylr.driver import RylrDriver
from app.infrastructure.lora.rylr.serial_at_port import SerialAtPort

logger = logging.getLogger(__name__)


class RylrFrameSource:
    def __init__(self, config: RylrConfig, driver: RylrDriver | None = None) -> None:
        self._config = config
        self._driver = driver
        self._closed = False

    async def frames(self) -> AsyncIterator[RawFrame]:
        driver = await asyncio.to_thread(self._ensure_driver)
        while not self._closed:
            packet = await asyncio.to_thread(driver.poll)
            if packet is None:
                continue
            yield RawFrame(
                payload=packet.payload,
                received_at=datetime.now(UTC),
                rssi=packet.rssi,
                snr=packet.snr,
            )

    async def close(self) -> None:
        self._closed = True
        if self._driver is not None:
            await asyncio.to_thread(self._driver.close)
            self._driver = None

    def _ensure_driver(self) -> RylrDriver:
        if self._driver is None:
            self._driver = RylrDriver(
                port=SerialAtPort(self._config.port, self._config.baud),
                config=self._config,
            )
        version = self._driver.start_receiving()
        logger.info(
            "rylr ready",
            extra={
                "version": version,
                "port": self._config.port,
                "frequency_hz": self._config.frequency_hz,
                "spreading_factor": self._config.spreading_factor,
                "network_id": self._config.network_id,
                "payload": self._config.payload,
            },
        )
        return self._driver
