from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "pi"]
LoraSource = Literal["sx1276", "rylr", "fake"]
RylrPayload = Literal["hex", "text", "node_csv"]
PushDelivery = Literal["expo", "log"]
LogFormat = Literal["json", "text"]
LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        extra="forbid",
    )

    environment: Environment = "local"
    enable_docs: bool = True

    release: str = "dev"
    """지금 돌고 있는 배포의 태그. deploy.sh가 data/release.env에 써서 주입한다.

    기본값이 "dev"인 것은 거짓말을 하지 않기 위해서다 — 주입이 없으면 태그를
    지어내는 대신 배포본이 아니라고 말한다.
    """

    log_level: LogLevel = "INFO"
    log_format: LogFormat = "text"

    database_path: Path = Path("data/orca.db")
    sqlite_busy_timeout_ms: int = 5_000

    lora_enabled: bool = True
    lora_source: LoraSource = "fake"
    lora_spi_bus: int = 0
    lora_spi_device: int = 0
    lora_reset_gpio: int = 22
    lora_frequency_hz: int = 922_000_000
    lora_spreading_factor: int = Field(default=9, ge=6, le=12)
    lora_bandwidth_hz: int = 125_000
    lora_coding_rate: int = Field(default=5, ge=5, le=8)
    lora_preamble_length: int = 8
    lora_sync_word: int = 0x12
    rylr_port: str = "/dev/ttyUSB0"
    rylr_baud: int = 115_200
    rylr_address: int = Field(default=1, ge=0, le=65535)
    rylr_network_id: int = Field(default=18, ge=3, le=18)
    rylr_payload: RylrPayload = "hex"
    rylr_node_hw_id: str = "000000000001"

    fake_node_hw_id: str = "aabbccddeeff"
    fake_interval_s: float = 3.0

    management_phone: str | None = None

    heartbeat_interval_s: int = 300
    offline_after_missed_beats: int = 3

    push_delivery: PushDelivery = "log"
    push_timeout_s: float = 10.0
    push_max_attempts: int = 3

    cors_allow_origins: tuple[str, ...] = ()

    @property
    def offline_threshold_s(self) -> int:
        return self.heartbeat_interval_s * self.offline_after_missed_beats

    @property
    def database_url(self) -> str:
        return f"sqlite+pysqlite:///{self.database_path}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
