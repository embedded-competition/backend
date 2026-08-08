---
name: backend-framework-alembic
description: Alembic 마이그레이션 리비전을 추가·검토·배포할 때 적용. SQLite ALTER 제약과 forward-only 정책 포함.
---
## Rule (마이그레이션이 스키마의 SSOT)
- 운영 스키마 변경은 Alembic 리비전으로만. `create_all()`·수동 `sqlite3` ALTER 금지.
- 리비전 파일은 커밋된 뒤 수정하지 않는다. 잘못됐으면 새 리비전으로 고친다(forward-only).
- 리비전 메시지는 무엇을 왜 바꾸는지: `alembic revision -m "add seq column for lora dedup"`.
- 한 리비전 = 논리적 변경 1개. 무관한 테이블 변경을 한 파일에 섞지 않는다.

## Rule (autogenerate 검토 의무)
- `alembic revision --autogenerate`는 초안 생성일 뿐이다. 생성된 파일을 반드시 읽고 수정한 뒤 커밋한다.
- autogenerate가 놓치는 것: 컬럼 이름 변경(drop+add로 오인해 데이터 소실), 제약 조건 변경, 서버 기본값, 인덱스 이름.
- 컬럼 이름 변경은 손으로 `op.alter_column(..., new_column_name=...)`을 쓴다. 생성된 drop+add를 그대로 두면 데이터가 날아간다.

## Rule (SQLite 특수 제약)
- SQLite는 `ALTER TABLE`이 제한적이다 — 컬럼 삭제·타입 변경·제약 추가가 직접 안 되거나 버전 의존적이다.
- 이런 변경은 `with op.batch_alter_table("t") as batch_op:` 블록을 쓴다. Alembic이 임시 테이블 복사 → 데이터 이관 → 이름 교체로 처리한다.
- batch 모드는 테이블을 통째로 복사한다. 시계열 테이블이 커진 상태에서 돌리면 RPi에서 오래 걸리고 디스크를 2배 쓴다 — 실행 전 행 수와 남은 디스크를 확인한다.
- `render_as_batch=True`를 `env.py`의 `context.configure`에 설정해 autogenerate가 batch 블록을 만들게 한다.

## Rule (파괴적 변경 — Expand/Contract)
- 컬럼 삭제·이름 변경은 한 배포에 몰지 않는다: ① 새 컬럼 추가 + 양쪽 쓰기 → ② 백필 → ③ 읽기 전환 → ④ 옛 컬럼 삭제.
- `NOT NULL` 컬럼 추가는 서버 기본값과 함께. 기본값 없이 추가하면 기존 행에서 실패한다.
- 백필은 리비전 안에서 배치로. 전체 UPDATE 한 방은 RPi에서 락을 길게 잡는다.

## Rule (배포 절차)
- 배포 순서: 서비스 중지 → **DB 파일 백업 복사** → `alembic upgrade head` → 서비스 시작.
- SQLite 백업은 파일 복사면 충분하다(WAL 파일 포함). 마이그레이션 실패 시 복구 경로가 이것뿐이므로 생략하지 않는다.
- `downgrade()`는 작성하되 운영 롤백 수단으로 신뢰하지 않는다. 롤백은 백업 복원이 정본.
- 앱 부팅 시 자동 `upgrade head` 실행하지 않는다 — 실패가 부팅 실패로 번지고 백업 시점이 사라진다.

## Anti-pattern
- 커밋된 리비전 파일 수정
- autogenerate 결과 무검토 커밋
- 컬럼 이름 변경이 drop+add로 생성된 채 배포 (데이터 소실)
- SQLite에서 batch 모드 없이 컬럼 삭제·타입 변경 시도
- `NOT NULL` 컬럼을 기본값 없이 추가
- 마이그레이션 전 DB 백업 생략
- 앱 startup에서 `alembic upgrade head` 자동 실행
- 한 리비전에 무관한 변경 여러 개
- `downgrade()` 미작성 또는 `pass`
