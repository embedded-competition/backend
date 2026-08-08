"""설정값 → FrameSource 선택.

하드웨어 없는 환경(Mac·CI·앱 팀 검증)에서 앱이 막히지 않도록 fake를 주입할 수 있다.
"""

from __future__ import annotations

import logging

from app.core.config import Settings
from app.domain.ports import FrameSource
from app.infrastructure.lora.radio import Sx1276FrameSource
from app.infrastructure.lora.registers import RadioConfig
from app.infrastructure.lora.scenario import ScenarioFrameFactory
from app.infrastructure.lora.sources import FakeFrameSource

logger = logging.getLogger(__name__)


def create_frame_source(settings: Settings) -> FrameSource:
    if settings.lora_source == "fake":
        logger.info(
            "lora fake source",
            extra={"hw_id": settings.fake_node_hw_id, "interval_s": settings.fake_interval_s},
        )
        return FakeFrameSource(
            ScenarioFrameFactory(settings.fake_node_hw_id),
            interval_s=settings.fake_interval_s,
        )
    return Sx1276FrameSource(radio_config(settings))


def radio_config(settings: Settings) -> RadioConfig:
    return RadioConfig(
        spi_bus=settings.lora_spi_bus,
        spi_device=settings.lora_spi_device,
        frequency_hz=settings.lora_frequency_hz,
        spreading_factor=settings.lora_spreading_factor,
        bandwidth_hz=settings.lora_bandwidth_hz,
        coding_rate=settings.lora_coding_rate,
        preamble_length=settings.lora_preamble_length,
        sync_word=settings.lora_sync_word,
    )
