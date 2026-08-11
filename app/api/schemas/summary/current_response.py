from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import Field

from app.api.schemas.channels import MeasuredValuesResponse
from app.domain.readings import Reading
from app.domain.value_objects import AlertState


class CurrentResponse(MeasuredValuesResponse):
    state: AlertState
    measured_at: Annotated[datetime, Field(description="노드가 측정한 시각 (UTC)")]

    @classmethod
    def from_domain(cls, reading: Reading) -> CurrentResponse:
        return cls(
            state=reading.state,
            measured_at=reading.measured_at,
            **MeasuredValuesResponse.fields_of(reading.frame),
        )
