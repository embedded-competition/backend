"""외부 시스템 port. 구현은 infrastructure에, 조립은 runtime에서.

Protocol은 구현이 2개 이상일 때만 만든다 — FrameSource(fake/sx1276)·
PushSender(logging/expo)·Clock(system/fixed)이 그 경우다. 저장소는 SQLAlchemy
구현 하나뿐이고 테스트도 실제 SQLite를 쓰므로 Protocol을 두지 않는다.

여기서 re-export하지 않는다 — 어댑터가 자기가 구현할 port만 import하도록
강제한다. `ports.frame_source`를 쓰는 라디오 드라이버가 PushSender를 알 이유가
없다.
"""
