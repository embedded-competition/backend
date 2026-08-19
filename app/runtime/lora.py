from __future__ import annotations

import logging
from collections.abc import Callable

from app.core.config import Settings
from app.domain.frames import TelemetryFrame
from app.domain.ports.frame_source import FrameSource, RawFrame
from app.infrastructure.lora.node_csv import NodeCsvParser
from app.infrastructure.lora.radio import Sx1276FrameSource
from app.infrastructure.lora.registers import RadioConfig
from app.infrastructure.lora.rylr import RylrConfig, RylrFrameSource
from app.runtime.receiver import parse_wire_frame

logger = logging.getLogger(__name__)


def create_frame_source(settings: Settings) -> FrameSource:
    """무선 어댑터만 고른다. `radio_enabled`가 거짓이면 호출되지 않는다."""
    if settings.lora_source == "rylr":
        return RylrFrameSource(rylr_config(settings))
    return Sx1276FrameSource(radio_config(settings))


def create_frame_parser(settings: Settings) -> Callable[[RawFrame], TelemetryFrame]:
    if settings.lora_source != "rylr" or settings.rylr_payload != "node_csv":
        return parse_wire_frame
    logger.warning(
        "node csv parser — 계약 이전 임시 경로",
        extra={
            "hw_id": settings.rylr_node_hw_id,
            "detail": "값이 정규화 편차가 아니라 원시 ADC다. 프레임 v2 전환 전까지만 쓴다",
        },
    )
    parser = NodeCsvParser(settings.rylr_node_hw_id)
    return lambda raw: parser.parse(raw.payload, raw.received_at)


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
