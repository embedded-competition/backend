---
name: poc
description: 검증되지 않은 기술·아이디어를 시간 박스로 실험해 결정(ADR)으로 변환할 때 사용. "PoC 해보자", "이 라이브러리 도입 검토", "알고리즘/모델 후보 비교", "성능 한계 측정", "결정 못 하는 trade-off 실험" 트리거. 실험 코드는 prod에 반영하지 않는다. 비-트리거 — 채택된 기능을 정식 구현(code workflow), 단발 벤치마크 실행, 이미 내려진 결정의 ADR 기록만(decision/ADR convention 직접).
---

# poc

## Purpose
- 검증되지 않은 기술/아이디어를 시간 박스로 실험해 측정값 기반 결정(ADR)으로 변환한다. 실험 코드는 prod에 들어가지 않는다.

## Procedure

### s0 Validate input — precondition
- 검증 대상이 다음 중 하나로 좁혀지는가: 새 라이브러리/프레임워크 도입, 알고리즘/모델 후보 비교, 외부 시스템 통합 가능성, 성능 한계 측정, 결정 못 하는 trade-off.
- 결정 책임자·기한·시간 박스를 정할 수 있는가.
- 충족 또는 추론 가능 → s1
- 누락 & 추론 불가 → 정지·요구 (outcome = needs-input)

### s1 Open decision issue
- Decision issue 생성: 질문, Context, 검토 옵션, 결정 책임자, 기한 명시.
- 자력 복구 불가 실패 → 정지·반환 (outcome = failed)

### s2 Scope the PoC
- 시간 박스 (예: 2일·1주).
- 성공 기준 정의 (측정 가능).
- 범위 외 작업 명시 (Non-Goals).

### s3 Create PoC branch
- PoC 브랜치 생성 (`spike/<topic>`). spike prefix는 merge 안 함 — 해당 규칙을 로드해 따른다.

### s4 Run experiment
- convention 준수는 완화 (시간 박스 우선).
- 단 secret leak·destructive 작업은 절대 금지.
- 결과는 측정값으로 기록 (수치·로그·screenshot).
- 시간 박스 초과 시 결정 책임자에 알림 + 범위 축소 또는 중단 결정.

### s5 Report results
- PoC report 작성 (`docs/tasks/<seq>-<topic>/poc-report.md`).
- 각 옵션의 측정값·trade-off·권장.

### s6 Write ADR — postcondition
- 산출 전 아래(Outputs)를 확인:
  - decision issue 존재.
  - PoC report 존재 (`docs/tasks/<seq>-<topic>/poc-report.md`) — 각 옵션의 측정값·trade-off·권장 포함.
  - ADR 작성 (채택·기각 모두 영구화), PoC report 인용. ADR 형식·기록 방식은 해당 규칙을 로드해 따른다.
- 미충족 → 이전 상태
- 충족 → ADR 작성·영구화, 결정 issue close(결론 + ADR ID + PR link), PoC 브랜치 폐기(merge X·삭제). 채택된 부분만 별 PR로 정식 구현. outcome = done

## Constraints
- 이 작업에 해당하는 규칙을 로드해 따른다 — 규칙 본문 미보유.
- 입력·산출 검증 실패 시 추측하지 않는다 — 정지·반환한다.
- 부분·미완 산출물을 내보내지 않는다 — 실패는 terminal 상태로 반환한다.
- PoC 코드를 그대로 main에 merge하지 않는다.
- 시간 박스를 무시하지 않는다.
- 측정 없이 "느낌"으로 결론 내지 않는다.
- 결정 책임자/기한을 누락하지 않는다.
- 시간 박스라도 secret commit·destructive 작업은 절대 금지.
- ADR 없이 결정을 종료하지 않는다 (구두 합의 X).
- PoC 결과를 다음 PoC가 인용 가능하도록 report로 정리한다.
