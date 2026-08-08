"""SX127x 레지스터 맵과 설정 인코딩. SPI·asyncio를 모른다."""

from __future__ import annotations

from dataclasses import dataclass

# 데이터시트 Table 41
OP_MODE = 0x01
FIFO = 0x00
FIFO_ADDR_PTR = 0x0D
FIFO_RX_CURRENT = 0x10
IRQ_FLAGS = 0x12
RX_NB_BYTES = 0x13
PKT_SNR = 0x19
PKT_RSSI = 0x1A
MODEM_CONFIG1 = 0x1D
MODEM_CONFIG2 = 0x1E
PREAMBLE_MSB = 0x20
PREAMBLE_LSB = 0x21
SYNC_WORD = 0x39
FRF_MSB = 0x06
VERSION = 0x42

MODE_SLEEP = 0x00
MODE_STDBY = 0x01
MODE_RX_CONTINUOUS = 0x05
LONG_RANGE_MODE = 0x80

IRQ_RX_DONE = 0x40
IRQ_PAYLOAD_CRC_ERROR = 0x20

EXPECTED_CHIP_VERSION = 0x12

_FSTEP = 32_000_000 / (1 << 19)
_BANDWIDTH_CODES = {
    7_800: 0,
    10_400: 1,
    15_600: 2,
    20_800: 3,
    31_250: 4,
    41_700: 5,
    62_500: 6,
    125_000: 7,
    250_000: 8,
    500_000: 9,
}


@dataclass(frozen=True, slots=True)
class RadioConfig:
    """노드 펌웨어와 값이 하나라도 어긋나면 수신 0이 된다 (docs/lora-frame.md)."""

    spi_bus: int
    spi_device: int
    frequency_hz: int
    spreading_factor: int
    bandwidth_hz: int
    coding_rate: int
    preamble_length: int
    sync_word: int
    poll_interval_s: float = 0.05


def frequency_words(hz: int) -> tuple[int, int, int]:
    """주파수를 FRF 레지스터 3바이트로."""
    frf = int(hz / _FSTEP)
    return (frf >> 16) & 0xFF, (frf >> 8) & 0xFF, frf & 0xFF


def modem_config1(config: RadioConfig) -> int:
    """bw[7:4] | codingRate[3:1] | implicitHeader[0]=0"""
    code = _BANDWIDTH_CODES.get(config.bandwidth_hz)
    if code is None:
        raise ValueError(f"지원하지 않는 대역폭: {config.bandwidth_hz}Hz")
    return (code << 4) | ((config.coding_rate - 4) << 1)


def modem_config2(config: RadioConfig) -> int:
    """sf[7:4] | txContinuous[3]=0 | rxPayloadCrc[2]=1 | symbTimeout[1:0]"""
    return (config.spreading_factor << 4) | 0x04


def decode_snr(raw: int) -> float:
    """PKT_SNR은 부호 있는 8비트, 1/4 dB 단위."""
    return (raw - 256 if raw > 127 else raw) / 4.0


def decode_rssi(raw: int) -> int:
    """HF 포트(>779MHz) 기준 보정."""
    return raw - 157
