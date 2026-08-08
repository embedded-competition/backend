---
name: backend-lora-ingest
description: SX1276 SPI 수신 어댑터와 수신 루프를 작성하거나 GPIO 인터럽트·재시작·멱등 저장·하드웨어 부재 환경 실행을 다룰 때 적용.
---
## Rule (어댑터 경계)
- 하드웨어 접근은 `app/infrastructure/lora/radio.py`에만. `spidev`·GPIO 라이브러리 import가 이 파일 밖으로 나가지 않는다.
- `radio.py`는 칩 제어만 한다 — 초기화, 레지스터 설정, 수신 대기, 원시 bytes 반환. 파싱·저장·판단 금지.
- 수신 어댑터는 domain Protocol(`FrameSource`)을 구현한다. 서비스는 Protocol만 안다.
- 개발 머신(Mac)에는 SPI가 없다. 설정값으로 fake 구현(`FileFrameSource`·`RandomFrameSource`)을 주입할 수 있어야 한다. 하드웨어 없이 API 개발이 막히면 안 된다.

## Rule (수신 루프)
- 수신은 `lifespan`에서 뜬 장수 asyncio task 1개. 요청 흐름과 분리한다.
- 루프 1회 = 프레임 1개 처리: 수신 → 파싱 → 서비스 호출 → 완료. 배치로 모았다가 처리하지 않는다(알람 지연).
- 프레임 1개 처리 실패가 루프를 죽이지 않는다. 예외를 잡고 로그 남기고 다음 프레임으로 간다.
- 단 `CancelledError`는 정리 후 재전파한다 — 종료가 안 되면 서비스가 안 내려간다.
- 연속 실패가 임계를 넘으면 라디오 재초기화를 시도하고, 그래도 실패하면 FAULT를 기록한다. 조용히 계속 돌지 않는다.

## Rule (blocking과 asyncio)
- `spidev` 읽기와 GPIO 대기는 blocking이다. 이벤트 루프를 막지 않게 `asyncio.to_thread` 또는 전용 스레드 + 큐로 넘긴다.
- DIO0 인터럽트 콜백은 다른 스레드에서 실행된다. 콜백 안에서 async 코드를 직접 호출하지 않는다 — `asyncio.run_coroutine_threadsafe` 또는 thread-safe 큐로 전달한다.
- 폴링으로 대체할 경우 간격을 설정값으로 두고, CPU 점유를 로그로 확인한다. Pi Zero 2W는 코어 여유가 적다.

## Rule (수신 후 처리)
- 저장은 멱등이어야 한다. `(device_id, measured_at, seq)` 유니크 제약 + `ON CONFLICT DO NOTHING`.
- `seq` 건너뜀은 유실로 기록한다. 유실률은 안테나·거리 문제의 유일한 관측 지표다.
- 상태 전이가 일어난 프레임만 알림 디스패치로 넘긴다. heartbeat는 저장만 한다.
- 알 수 없는 `device_id`는 거절하고 로그를 남긴다. 미등록 장비를 자동 등록하지 않는다.

## Rule (라디오 파라미터)
- 주파수·SF·대역폭·코딩레이트·프리앰블·sync word는 전부 설정값. 코드 상수 하드코딩 금지.
- 노드 펌웨어와 값이 하나라도 어긋나면 수신 0이 된다. 설정 기본값과 노드 펌웨어 값을 같은 문서(`docs/lora-frame.md`)에 함께 적는다.
- 한국 ISM 대역·duty cycle 제약을 설정 주석에 명시한다.

## Rule (관측)
- 부팅 시 라디오 초기화 결과(칩 version 레지스터 읽기)를 INFO 로그로 남긴다. 배선 문제를 여기서 잡는다.
- 프레임마다 RSSI·SNR을 저장한다. 통신 품질 저하가 알람 유실의 선행 지표다.
- 수신 카운터(성공·CRC실패·파싱실패·중복)를 주기적으로 로그에 남긴다.

## Anti-pattern
- `spidev` import가 `core/`·`api/`에 등장
- 하드웨어 없으면 앱이 아예 안 뜸 (fake 주입 경로 없음)
- 수신 루프에서 예외 발생 시 task 사망 후 조용히 수신 중단
- `CancelledError`를 삼켜 종료 불가
- blocking SPI 읽기를 이벤트 루프에서 직접 호출
- GPIO 콜백 스레드에서 async 함수 직접 호출
- 중복 프레임을 그대로 insert
- `seq` 유실을 기록하지 않음
- 미등록 device_id 자동 등록
- 주파수·SF를 코드에 하드코딩
- RSSI·SNR 미저장 (품질 저하 원인 추적 불가)
