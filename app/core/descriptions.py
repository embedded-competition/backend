"""이벤트 문구 생성. 서버 책임이다 (앱 C5 — 앱에 박으면 수정 시 스토어 심사)."""

from __future__ import annotations

from app.domain.value_objects import AlertState

_STATE_LABEL = {
    AlertState.WARMUP: "예열",
    AlertState.NORMAL: "정상",
    AlertState.WATCH: "주의",
    AlertState.ALARM: "경보",
    AlertState.FAULT: "고장",
}


def describe_transition(from_state: AlertState, to_state: AlertState) -> str:
    return f"{_STATE_LABEL[from_state]} → {_STATE_LABEL[to_state]} 전환"


def describe_release(note: str | None) -> str:
    return "사용자 요청으로 경보 해제됨" + (f" ({note})" if note else "")


def describe_suppression(reason: str) -> str:
    return f"{reason}으로 승격 보류 (오경보 아님)"
