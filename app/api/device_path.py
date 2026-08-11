from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Path

from app.domain.device import Device
from app.runtime.providers import DeviceServiceDep

MacPath = Annotated[
    str,
    Path(
        min_length=12,
        max_length=17,
        description="점검장비 라벨의 MAC 주소. 구분자는 서버가 정규화한다",
        examples=["AA:BB:CC:DD:EE:FF"],
    ),
]


def device_by_mac_dep(mac: MacPath, devices: DeviceServiceDep) -> Device:
    return devices.get_by_mac(mac)


ResolvedDevice = Annotated[Device, Depends(device_by_mac_dep)]
