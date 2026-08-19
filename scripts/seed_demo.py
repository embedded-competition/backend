"""클라이언트가 화면을 확인할 수 있도록 시연용 기기와 관측을 채운다.

실기기가 하나뿐이라 앱은 정상 화면밖에 볼 수 없다. 경보·정비요망·가스누출
같은 상태를 손으로 만들 방법이 없으면 그 화면들은 배포 전까지 한 번도
확인되지 않는다.

MAC이 00:00:00:00:00:* 인 기기만 만들고 지운다. 실기기는 이 접두사를 쓸 수
없으므로(제조사 OUI가 아니다) 실데이터와 섞이지 않는다.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.domain.alerting import Alert, Event
from app.domain.device import Device
from app.domain.frames import TelemetryFrame
from app.domain.measurements import Measure
from app.domain.readings import RadioQuality, Reading
from app.domain.value_objects import AlertState, Condition, EventKind
from app.infrastructure.db.orm import AlertOrm, DeviceOrm, EventOrm, ReadingOrm
from app.infrastructure.db.repositories.alerts import SqlAlchemyAlertRepository
from app.infrastructure.db.repositories.devices import SqlAlchemyDeviceRepository
from app.infrastructure.db.repositories.events import SqlAlchemyEventRepository
from app.infrastructure.db.repositories.readings import SqlAlchemyReadingRepository
from app.infrastructure.db.session import create_db_engine, create_session_factory
from app.simulation import TEST_MAC_PREFIX

DEMO_MAC_PREFIX = TEST_MAC_PREFIX

_FRAME_VERSION = 0
_HISTORY = timedelta(hours=48)
_EVERY = timedelta(minutes=10)

_BASELINE = {
    Measure.VOC_DEV: 30_000.0,
    Measure.H2_DEV: 2_500.0,
    Measure.CO_DEV: 580.0,
    Measure.PRESSURE_DEV: 200.0,
}


@dataclass(frozen=True, slots=True)
class Scenario:
    """앱이 확인해야 하는 화면 하나에 기기 하나를 대응시킨다."""

    mac: str
    label: str
    slot: str
    state: AlertState
    conditions: frozenset[Condition]
    rise: float
    latched: bool = False
    water: bool = False

    @property
    def public_id(self) -> str:
        return f"demo-{self.mac.replace(':', '')[-2:]}"


SCENARIOS = (
    Scenario(
        mac=f"{DEMO_MAC_PREFIX}01",
        label="시연 1호기 — 정상",
        slot="B2-01",
        state=AlertState.NORMAL,
        conditions=frozenset(),
        rise=0.0,
    ),
    Scenario(
        mac=f"{DEMO_MAC_PREFIX}02",
        label="시연 2호기 — 가스 누출",
        slot="B2-02",
        state=AlertState.WATCH,
        conditions=frozenset({Condition.CO_RISE, Condition.VOC_RISE}),
        rise=0.45,
    ),
    Scenario(
        mac=f"{DEMO_MAC_PREFIX}03",
        label="시연 3호기 — 경보 (해제 대기)",
        slot="B2-03",
        state=AlertState.ALARM,
        conditions=frozenset({Condition.CO_RISE, Condition.H2_RISE, Condition.VOC_RISE}),
        rise=1.6,
        latched=True,
    ),
    Scenario(
        mac=f"{DEMO_MAC_PREFIX}04",
        label="시연 4호기 — 센서 점검 필요",
        slot="B2-04",
        state=AlertState.FAULT,
        conditions=frozenset({Condition.SENSOR_FAULT}),
        rise=0.0,
    ),
    Scenario(
        mac=f"{DEMO_MAC_PREFIX}05",
        label="시연 5호기 — 침수",
        slot="B2-05",
        state=AlertState.WATCH,
        conditions=frozenset({Condition.WATER}),
        rise=0.1,
        water=True,
    ),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="시연 기기의 기존 관측·기록을 지우고 다시 채운다",
    )
    args = parser.parse_args()

    settings = Settings()
    engine = create_db_engine(
        settings.database_path, busy_timeout_ms=settings.sqlite_busy_timeout_ms
    )
    now = datetime.now(UTC)

    with create_session_factory(engine)() as session, session.begin():
        if args.reset:
            removed = _clear(session)
            print(f"시연 데이터 삭제: 기기 {removed}대")
        for scenario in SCENARIOS:
            device = _upsert_device(session, scenario, now)
            readings = _fill_readings(session, device, scenario, now)
            events = _fill_events(session, device, scenario, now)
            print(f"{scenario.mac}  관측 {readings:4d}  기록 {events}  {scenario.label}")
    return 0


def _clear(session: Session) -> int:
    """시연 기기만 지운다. 자식 행이 남으면 FK가 끊긴 고아가 된다."""
    ids = list(
        session.scalars(select(DeviceOrm.id).where(DeviceOrm.mac.startswith(DEMO_MAC_PREFIX)))
    )
    if not ids:
        return 0
    for table in (EventOrm, AlertOrm, ReadingOrm):
        session.execute(delete(table).where(table.device_id.in_(ids)))
    session.execute(delete(DeviceOrm).where(DeviceOrm.id.in_(ids)))
    return len(ids)


def _upsert_device(session: Session, scenario: Scenario, now: datetime) -> Device:
    devices = SqlAlchemyDeviceRepository(session)
    found = devices.get_by_mac(scenario.mac)
    device = found or Device(
        public_id=scenario.public_id,
        mac=scenario.mac,
        label=scenario.label,
        parking_slot=scenario.slot,
        registered_at=now - _HISTORY,
    )
    device.label = scenario.label
    device.parking_slot = scenario.slot
    device.last_seen_at = now
    device.last_state = scenario.state
    return devices.save(device)


def _fill_readings(session: Session, device: Device, scenario: Scenario, now: datetime) -> int:
    readings = SqlAlchemyReadingRepository(session)
    stored = 0
    for seq, at in enumerate(_ticks(now), start=1):
        progress = seq * _EVERY / _HISTORY
        frame = TelemetryFrame(
            version=_FRAME_VERSION,
            seq=seq,
            measured_at=at,
            state=scenario.state if _is_recent(at, now) else AlertState.NORMAL,
            conditions=scenario.conditions if _is_recent(at, now) else frozenset(),
            latched=scenario.latched and _is_recent(at, now),
            water=scenario.water and _is_recent(at, now),
            values=_values(scenario, progress),
        )
        if readings.add_if_absent(
            Reading(
                device_id=device.key,
                frame=frame,
                received_at=at,
                radio=RadioQuality(rssi=-42, snr=9.5),
            )
        ):
            stored += 1
    return stored


def _ticks(now: datetime) -> Iterator[datetime]:
    at = now - _HISTORY
    while at <= now:
        yield at
        at += _EVERY


def _is_recent(at: datetime, now: datetime) -> bool:
    """상태는 마지막 6시간에만 준다 — 48시간 내내 경보면 차트가 평평해진다."""
    return at >= now - timedelta(hours=6)


def _values(scenario: Scenario, progress: float) -> dict[Measure, float]:
    """기준선에서 시나리오의 상승분만큼 올린다. 뒤로 갈수록 가파르다."""
    ramp = scenario.rise * progress**3
    return {measure: base * (1.0 + ramp) for measure, base in _BASELINE.items()}


def _fill_events(session: Session, device: Device, scenario: Scenario, now: datetime) -> int:
    events = SqlAlchemyEventRepository(session)
    alerts = SqlAlchemyAlertRepository(session)
    written = 0

    if scenario.state is AlertState.NORMAL:
        return written

    occurred = now - timedelta(hours=5)
    alert = alerts.add(
        Alert(
            device_id=device.key,
            from_state=AlertState.NORMAL,
            to_state=scenario.state,
            occurred_at=occurred,
            detected_at=occurred,
        )
    )
    events.add(
        Event(
            device_id=device.key,
            kind=EventKind.STATE_CHANGE,
            occurred_at=occurred,
            description=_state_change_text(scenario.state),
            alert_id=alert.key,
        )
    )
    written += 1

    events.add(
        Event(
            device_id=device.key,
            kind=EventKind.ACTION,
            occurred_at=occurred + timedelta(minutes=1),
            description="관리자에게 알림을 보냈습니다",
        )
    )
    written += 1

    if scenario.latched:
        events.add(
            Event(
                device_id=device.key,
                kind=EventKind.ACTION,
                occurred_at=occurred + timedelta(seconds=5),
                description="충전 전원을 자동으로 껐습니다",
            )
        )
        written += 1

    return written


def _state_change_text(state: AlertState) -> str:
    return {
        AlertState.ALARM: "화재 발생 직전 상태로 바뀌었습니다",
        AlertState.WATCH: "이상 징후가 감지됐습니다",
        AlertState.FAULT: "센서를 믿을 수 없는 상태가 됐습니다",
    }.get(state, "상태가 바뀌었습니다")


if __name__ == "__main__":
    sys.exit(main())
