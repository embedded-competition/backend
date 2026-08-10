"""vulture whitelist — "쓰이지 않는 것처럼 보이지만 살아 있는" 심볼.

세 부류다. dataclass·Pydantic·ORM 필드 선언(생성된 __init__이 대입하므로 정적
분석에는 대입만 보인다), 프레임워크가 이름으로 호출하는 것(Alembic upgrade/downgrade,
SQLAlchemy TypeDecorator), 그리고 코드보다 넓은 계약에 묶인 값(EventKind.SUPPRESSED —
앱 계약과 ck_events_kind 제약이 이미 포함하므로 서버 경로가 없다고 지우면 두 곳이
어긋난다).

스캔 대상은 app·migrations·scripts다. tests를 넣으면 테스트만 부르는 코드가 살아
있는 것으로 보여, 어떤 유스케이스도 쓰지 않는 규칙이 조용히 쌓인다.

이 파일이 잡음을 흡수해야 제품 경로에서 새로 죽는 코드가 vulture 출력에 단독으로
드러난다. 재생성: 이 파일을 `# ruff: noqa` 한 줄로 비운 뒤
`uv run vulture --make-whitelist > vulture_whitelist.py`, 그리고 이 머리말 복원.
"""

# ruff: noqa
released  # unused variable (app/api/schemas/alarm.py:15)
model_config  # unused variable (app/api/schemas/base.py:8)
model_config  # unused variable (app/api/schemas/base.py:17)
error  # unused variable (app/api/schemas/base.py:19)
requestId  # unused variable (app/api/schemas/base.py:20)
temp_c  # unused variable (app/api/schemas/channels/env_response.py:11)
d_rh_dt  # unused variable (app/api/schemas/channels/env_response.py:13)
dev_z  # unused variable (app/api/schemas/channels/gas_channel_response.py:11)
pres_dev  # unused variable (app/api/schemas/channels/pressure_response.py:7)
pres_rate  # unused variable (app/api/schemas/channels/pressure_response.py:8)
model_config  # unused variable (app/api/schemas/device.py:11)
device_token  # unused variable (app/api/schemas/device.py:28)
model_config  # unused variable (app/api/schemas/device.py:47)
registered  # unused variable (app/api/schemas/device.py:61)
model_config  # unused variable (app/api/schemas/health.py:17)
detail  # unused variable (app/api/schemas/health.py:20)
model_config  # unused variable (app/api/schemas/health.py:27)
revision  # unused variable (app/api/schemas/health.py:31)
gas  # unused variable (app/api/schemas/history.py:19)
h2  # unused variable (app/api/schemas/history.py:20)
co  # unused variable (app/api/schemas/history.py:21)
temp_c  # unused variable (app/api/schemas/history.py:22)
pres_dev  # unused variable (app/api/schemas/history.py:24)
node_id  # unused variable (app/api/schemas/telemetry.py:24)
last_seen  # unused variable (app/api/schemas/telemetry.py:29)
gas  # unused variable (app/api/schemas/telemetry.py:62)
h2  # unused variable (app/api/schemas/telemetry.py:63)
co  # unused variable (app/api/schemas/telemetry.py:64)
env  # unused variable (app/api/schemas/telemetry.py:65)
pressure  # unused variable (app/api/schemas/telemetry.py:66)
module  # unused variable (app/api/schemas/telemetry.py:70)
model_config  # unused variable (app/core/config.py:14)
attempted  # unused variable (app/core/notification_service.py:20)
unit  # unused variable (app/domain/measurements/measure_spec.py:11)
SUPPRESSED  # unused variable (app/domain/value_objects/event_kind.py:9)
h2_dev  # unused variable (app/infrastructure/db/orm.py:70)
h2_slope  # unused variable (app/infrastructure/db/orm.py:71)
co_dev  # unused variable (app/infrastructure/db/orm.py:72)
co_slope  # unused variable (app/infrastructure/db/orm.py:73)
temp_c  # unused variable (app/infrastructure/db/orm.py:80)
humidity_pct  # unused variable (app/infrastructure/db/orm.py:81)
d_rh_dt  # unused variable (app/infrastructure/db/orm.py:82)
pressure_dev  # unused variable (app/infrastructure/db/orm.py:83)
pressure_rate  # unused variable (app/infrastructure/db/orm.py:84)
impl  # unused variable (app/infrastructure/db/types.py:10)
cache_ok  # unused variable (app/infrastructure/db/types.py:11)
_.mode  # unused attribute (app/infrastructure/lora/spi.py:21)
crc_error  # unused variable (app/infrastructure/lora/stats.py:11)
parse_error  # unused variable (app/infrastructure/lora/stats.py:12)
unknown_device  # unused variable (app/infrastructure/lora/stats.py:13)
_.unknown_device  # unused attribute (app/runtime/receiver.py:64)
_.crc_error  # unused attribute (app/runtime/receiver.py:97)
_.parse_error  # unused attribute (app/runtime/receiver.py:99)
revision  # unused variable (migrations/versions/8afee99947f7_app_contract_alignment_auth_tokens_.py:29)
down_revision  # unused variable (migrations/versions/8afee99947f7_app_contract_alignment_auth_tokens_.py:30)
branch_labels  # unused variable (migrations/versions/8afee99947f7_app_contract_alignment_auth_tokens_.py:31)
depends_on  # unused variable (migrations/versions/8afee99947f7_app_contract_alignment_auth_tokens_.py:32)
revision  # unused variable (migrations/versions/f6dff04dd32d_initial_schema_devices_readings_alerts_.py:20)
down_revision  # unused variable (migrations/versions/f6dff04dd32d_initial_schema_devices_readings_alerts_.py:21)
branch_labels  # unused variable (migrations/versions/f6dff04dd32d_initial_schema_devices_readings_alerts_.py:22)
depends_on  # unused variable (migrations/versions/f6dff04dd32d_initial_schema_devices_readings_alerts_.py:23)
_.process_result_value  # unused method (app/infrastructure/db/types.py:21)
_.process_bind_param  # unused method (app/infrastructure/db/types.py:13)
downgrade  # unused function (migrations/versions/f6dff04dd32d_initial_schema_devices_readings_alerts_.py:147)
downgrade  # unused function (migrations/versions/8afee99947f7_app_contract_alignment_auth_tokens_.py:140)
upgrade  # unused function (migrations/versions/8afee99947f7_app_contract_alignment_auth_tokens_.py:35)
upgrade  # unused function (migrations/versions/f6dff04dd32d_initial_schema_devices_readings_alerts_.py:26)
