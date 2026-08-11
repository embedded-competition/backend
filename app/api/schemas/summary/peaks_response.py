from __future__ import annotations

from app.api.schemas.base import ApiModel
from app.api.schemas.summary.channel_peak_response import ChannelPeakResponse
from app.core.period_summary import PeriodSummary
from app.domain.value_objects import GasChannel


class PeaksResponse(ApiModel):
    gas: ChannelPeakResponse | None = None
    h2: ChannelPeakResponse | None = None
    co: ChannelPeakResponse | None = None

    @classmethod
    def from_domain(cls, summary: PeriodSummary) -> PeaksResponse:
        return cls(
            gas=_peak(summary, GasChannel.VOC),
            h2=_peak(summary, GasChannel.H2),
            co=_peak(summary, GasChannel.CO),
        )


def _peak(summary: PeriodSummary, channel: GasChannel) -> ChannelPeakResponse | None:
    peak = summary.peak(channel)
    return ChannelPeakResponse.from_domain(peak) if peak else None
