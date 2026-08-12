from __future__ import annotations

from enum import StrEnum

from app.domain.value_objects.condition import Condition


class Stage(StrEnum):
    """화재로 가는 진행 단계. 값의 나열 순서가 곧 진행 순서다.

    Condition이 "무엇이 일어나는가"를 순서 없이 모아둔 것이라면, Stage는
    "어디까지 왔는가"를 하나로 답한다. 앱 화면은 이 단계까지 칸을 채운다.
    """

    NONE = "NONE"
    TEMP_RISE = "TEMP_RISE"
    GAS_LEAK = "GAS_LEAK"
    RAPID_WORSENING = "RAPID_WORSENING"
    IGNITION = "IGNITION"

    @classmethod
    def from_conditions(cls, conditions: frozenset[Condition]) -> Stage | None:
        """판정할 수 있을 때만 답한다.

        None은 "모른다"이지 "이상 없음"이 아니다 — NONE과 구별된다. 지금 노드가
        보내는 신호로 확정할 수 있는 단계는 NONE과 GAS_LEAK 둘뿐이고, 나머지는
        프레임 v2의 온도·기울기가 와야 판정된다. 그때까지 모르는 것을 안다고 하지 않는다.
        """
        if conditions & _GAS:
            return cls.GAS_LEAK
        if conditions & _UNDECIDABLE:
            return None
        return cls.NONE


_GAS = frozenset({Condition.CO_RISE, Condition.H2_RISE, Condition.VOC_RISE})

_UNDECIDABLE = frozenset({Condition.PRESSURE_RISE, Condition.UNKNOWN})
"""단계 축에 속하지만 아직 어느 칸인지 정할 규칙이 없는 것들.

PRESSURE_RISE(팽창)는 화면 5칸 어디에도 대응이 없고, UNKNOWN은 정의상 모른다.
둘 다 이상이 있다는 뜻이므로 NONE("이상 없음")으로 접으면 거짓말이 된다.
WATER·SENSOR_FAULT는 화재 진행이 아니라 다른 축이라 여기 없다 — status가 답한다.
"""
