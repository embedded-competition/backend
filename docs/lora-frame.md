| offset | size | 필드 | 타입 | 값 | 노드 산출식 |
|---|---|---|---|---|---|
| 0 | 6 | `mac` | uint8[6] | — | `esp_read_mac(ESP_MAC_WIFI_STA)` |
| 6 | 2 | `mq7` | uint16 | 0~1000 | `filtered * 1000 / 4095` |
| 8 | 2 | `mq8` | uint16 | 0~1000 | `filtered * 1000 / 4095` |
| 10 | 2 | `pressure` | uint16 | 0~1000 | `filtered * 1000 / 4095` (FSR402) |
| 12 | 2 | `water` | uint16 | 0~1000 | `filtered * 1000 / 4095` |
| 14 | 2 | `voc` | uint16 | 0~1000 | `(1 - filtered / 65535) * 1000` (SGP40, 반전) |
| 16 | 4 | `lat` | float32 | ±90 | 미장착 |
| 20 | 4 | `lon` | float32 | ±180 | 미장착 |
| 24 | 2 | `crc` | uint16 | — | CRC-16/CCITT-FALSE, 대상 0~23 |
| — | **26** | **합계** | | | base64url **35자** |

## 무선 파라미터는 노드와 글자 그대로 같아야 한다

노드 펌웨어(`embedded/main/hello_world_main.c`)가 모듈에 거는 값이 기준이다.

| 항목 | 노드 AT 명령 | 서버 설정 |
|---|---|---|
| 대역 | `AT+BAND=922100000` | `APP_LORA_FREQUENCY_HZ=922100000` |
| 네트워크 | `AT+NETWORKID=18` | `APP_RYLR_NETWORK_ID=18` |
| 주소 | 노드 `AT+ADDRESS=1`, 수신처 2 | `APP_RYLR_ADDRESS=2` |
| SF·BW·CR·프리앰블 | `AT+PARAMETER=9,7,1,12` | SF 9 / 125kHz / CR 5 / 프리앰블 **12** |

프리앰블이 어긋나면 수신이 0이 된다. 에러가 아니라 무음이라 로그에 아무 흔적이
남지 않는다 — 실제로 v0.6.9까지 서버가 8을 걸고 있었고, 그동안 한 장도 못 받았다.
