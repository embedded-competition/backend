from __future__ import annotations

import logging

from app.core.config import Settings
from app.domain.ports.frame_source import FrameSource
from app.infrastructure.lora.radio import Sx1276FrameSource
from app.infrastructure.lora.registers import RadioConfig
from app.infrastructure.lora.rylr import RylrConfig, RylrFrameSource
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
    if settings.lora_source == "rylr":
        return RylrFrameSource(rylr_config(settings))
    return Sx1276FrameSource(radio_config(settings))


def rylr_config(settings: Settings) -> RylrConfig:
    return RylrConfig(
        port=settings.rylr_port,
        baud=settings.rylr_baud,
        address=settings.rylr_address,
        network_id=settings.rylr_network_id,
        frequency_hz=settings.lora_frequency_hz,
        spreading_factor=settings.lora_spreading_factor,
        bandwidth_hz=settings.lora_bandwidth_hz,
        coding_rate=settings.lora_coding_rate,
        preamble_length=settings.lora_preamble_length,
        payload=settings.rylr_payload,
    )


def radio_config(settings: Settings) -> RadioConfig:
    return RadioConfig(
        spi_bus=settings.lora_spi_bus,
        spi_device=settings.lora_spi_device,
        reset_gpio=settings.lora_reset_gpio,
        frequency_hz=settings.lora_frequency_hz,
        spreading_factor=settings.lora_spreading_factor,
        bandwidth_hz=settings.lora_bandwidth_hz,
        coding_rate=settings.lora_coding_rate,
        preamble_length=settings.lora_preamble_length,
        sync_word=settings.lora_sync_word,
    )
