"""환경 설정 SSOT. 코드 어디서도 os.getenv를 직접 호출하지 않는다."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

Environment = Literal["local", "pi"]
LoraSource = Literal["sx1276", "fake"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        extra="forbid",  # 오타 난 환경변수가 조용히 무시되지 않게
    )

    environment: Environment = "local"
    # 인터넷 터널 노출 상태이므로 Pi에서는 명시적으로 꺼야 한다.
    enable_docs: bool = True

    # --- 데이터베이스 -------------------------------------------------
    database_path: Path = Path("data/orca.db")
    sqlite_busy_timeout_ms: int = 5_000

    # --- LoRa (SX1276 SPI) --------------------------------------------
    # 노드 펌웨어와 값이 하나라도 어긋나면 수신 0이 된다.
    # 기준값은 docs/lora-frame.md와 함께 관리한다.
    # 수신 task 자체를 끌 수 있게 한다 — API만 띄우는 환경·테스트용
    lora_enabled: bool = True
    lora_source: LoraSource = "fake"
    lora_spi_bus: int = 0
    lora_spi_device: int = 0
    lora_dio0_gpio: int = 25
    lora_reset_gpio: int = 22
    # 한국 ISM 대역 917.0~923.5MHz. duty cycle 제약 준수 필요.
    lora_frequency_hz: int = 922_000_000
    lora_spreading_factor: int = Field(default=7, ge=6, le=12)
    lora_bandwidth_hz: int = 125_000
    lora_coding_rate: int = Field(default=5, ge=5, le=8)
    lora_preamble_length: int = 8
    lora_sync_word: int = 0x12
    # fake source — 하드웨어 없이 앱 전 화면을 검증하기 위한 합성 데이터
    fake_node_hw_id: str = "aabbccddeeff"
    fake_interval_s: float = 3.0

    # --- 운영 정보 -----------------------------------------------------
    # 등록 시 앱에 내려주는 관리실 번호. 앱에 하드코딩하지 않기 위해 서버가 소유한다.
    management_phone: str | None = None

    # --- 노드 생존 판정 -----------------------------------------------
    # 펌웨어 확정 시 조정. 스키마는 이 값에 무관하다.
    heartbeat_interval_s: int = 300
    offline_after_missed_beats: int = 3

    # --- 푸시 (FCM) ---------------------------------------------------
    # 비밀값에 기본값을 주지 않는다 — 없으면 부팅이 실패해야 한다.
    fcm_credentials_path: Path | None = None
    fcm_project_id: SecretStr | None = None
    push_timeout_s: float = 10.0
    push_max_attempts: int = 3

    # --- CORS ---------------------------------------------------------
    # 앱 origin만 명시 허용. "*" + credentials 조합 금지.
    cors_allow_origins: tuple[str, ...] = ()

    @property
    def offline_threshold_s(self) -> int:
        return self.heartbeat_interval_s * self.offline_after_missed_beats

    @property
    def database_url(self) -> str:
        return f"sqlite+pysqlite:///{self.database_path}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """설정 접근 단일 진입점. 모듈 전역 인스턴스를 만들지 않는다."""
    return Settings()
