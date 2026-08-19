from __future__ import annotations

from enum import StrEnum


class BucketLevel(StrEnum):
    """차트 한 칸이 어느 정도인가. 앱은 이 값으로 칸을 색칠한다.

    status(사용자 행동)나 stage(진행 단계)와 다른 축이다. 저 둘은 기기 전체를
    말하지만 이것은 센서 하나의 한 구간만 말한다.
    """

    NORMAL = "NORMAL"
    CAUTION = "CAUTION"
    DANGER = "DANGER"
