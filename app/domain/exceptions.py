"""도메인 예외. HTTP 상태 코드를 알지 않는다 — 매핑은 api 계층."""

from __future__ import annotations


class DomainError(Exception):
    """모든 도메인 예외의 베이스."""

    code = "DOMAIN_ERROR"


class DeviceNotFound(DomainError):
    code = "DEVICE_NOT_FOUND"


class DeviceNotRegistered(DomainError):
    """미등록 노드가 프레임을 보냈다. 자동 등록하지 않는다."""

    code = "DEVICE_NOT_REGISTERED"


class DeviceInactive(DomainError):
    code = "DEVICE_INACTIVE"


class AlertNotFound(DomainError):
    code = "ALERT_NOT_FOUND"


class AlertAlreadyAcknowledged(DomainError):
    code = "ALERT_ALREADY_ACKNOWLEDGED"


class FrameError(DomainError):
    """LoRa 프레임 처리 실패. 원인별로 구분해야 분석이 가능하다."""

    code = "FRAME_ERROR"


class FrameTooShort(FrameError):
    code = "FRAME_TOO_SHORT"


class FrameCrcError(FrameError):
    code = "FRAME_CRC_ERROR"


class UnsupportedFrameVersion(FrameError):
    code = "UNSUPPORTED_FRAME_VERSION"


class FrameFieldError(FrameError):
    """길이·CRC·version은 통과했으나 필드 값이 범위를 벗어남."""

    code = "FRAME_FIELD_ERROR"
