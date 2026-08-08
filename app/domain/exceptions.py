"""도메인 예외. HTTP 상태 코드를 알지 않는다 — 매핑은 api 계층.

`code`는 앱이 분기에 쓰는 계약값이다 (앱 api-spec.md §공통 에러).
값을 바꾸면 파괴적 변경 — 앱 수정과 동반돼야 한다.
"""

from __future__ import annotations


class DomainError(Exception):
    """모든 도메인 예외의 베이스."""

    code = "internal_error"


class Unauthorized(DomainError):
    """deviceToken 없음 또는 유효하지 않음."""

    code = "unauthorized"


class DeviceNotFound(DomainError):
    code = "device_not_found"


class InvalidMac(DomainError):
    """MAC 형식이 아니다. 앱이 입력을 고쳐 재시도할 수 있다."""

    code = "invalid_mac"


class DeviceAlreadyPaired(DomainError):
    """이미 등록된 MAC. 앱 spec §② POST /devices 409."""

    code = "already_paired"


class DeviceNotRegistered(DomainError):
    """미등록 노드가 프레임을 보냈다. 자동 등록하지 않는다."""

    code = "device_not_registered"


class DeviceInactive(DomainError):
    code = "device_inactive"


class AlertNotFound(DomainError):
    code = "alert_not_found"


class AlertAlreadyAcknowledged(DomainError):
    code = "alert_already_acknowledged"


class ReleaseNotAllowed(DomainError):
    """경보 해제 거부. 사유는 앱에 내려주지 않는다 (앱 spec O8)."""

    code = "not_allowed"


class FrameError(DomainError):
    """LoRa 프레임 처리 실패. 원인별로 구분해야 분석이 가능하다."""

    code = "frame_error"


class FrameTooShort(FrameError):
    code = "frame_too_short"


class FrameCrcError(FrameError):
    code = "frame_crc_error"


class UnsupportedFrameVersion(FrameError):
    code = "unsupported_frame_version"


class FrameFieldError(FrameError):
    """길이·CRC·version은 통과했으나 필드 값이 범위를 벗어남."""

    code = "frame_field_error"
