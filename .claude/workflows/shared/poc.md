---
name: shared-poc
description: 검증되지 않은 기술·아이디어를 시간 박스로 실험해 결정(ADR)으로 변환할 때 사용.
---
## 목적
검증되지 않은 기술/아이디어를 빠르게 실험해 **결정(ADR)으로 변환**하는 절차. PoC 코드는 prod에 들어가지 않음.

## 시작 trigger
- 새 라이브러리/프레임워크 도입 검토
- 알고리즘/모델 후보 비교 (SLAM 알고리즘, ML 모델)
- 외부 시스템 통합 가능성 검증
- 성능 한계 측정 (load test, latency)
- 사용자가 결정 못 하는 trade-off → decision 이슈 (git/issue.md의 decision template)

## 절차
1. **Decision issue 생성** (`.github/ISSUE_TEMPLATE/decision.yml`)
   - 질문, Context, 검토 옵션, 결정 책임자, 기한 명시
2. **PoC 범위 한정**
   - 시간 박스 (예: 2일·1주)
   - 성공 기준 정의 (측정 가능)
   - 범위 외 작업 명시 (Non-Goals)
3. **PoC 브랜치 생성** (`spike/<topic>`)
   - convention: `git/branch.md` (spike prefix는 merge 안 함)
4. **실험 실행**
   - convention 준수는 완화 (시간 박스 우선)
   - 단 secret leak·destructive 작업은 절대 금지
   - 결과는 측정값으로 기록 (수치·로그·screenshot)
5. **결과 보고**
   - `docs/tasks/<seq>-<topic>/poc-report.md` 작성
   - 각 옵션의 측정값·trade-off·권장
6. **ADR 작성** (`docs/decisions/NNNN-*.md`)
   - convention: `docs/ard.md`
   - PoC report 인용
7. **결정 issue close**
   - 결론 + ADR ID + PR link
8. **PoC 브랜치 폐기**
   - merge X. 브랜치 삭제
   - 채택된 부분만 별 PR로 정식 구현 (workflows/code.md)

## 시간 박스 정책
| 범위 | 기간 |
|---|---|
| 1 옵션 spike | ≤ 2일 |
| 다중 옵션 비교 | ≤ 1주 |
| 큰 아키텍처 검증 | ≤ 2주 (초과 시 ADR로 sub-decision 분할) |

기간 초과 시 결정 책임자에 알림 + 범위 축소 또는 중단 결정.

## 산출물 (필수)
- decision issue
- PoC report (`docs/tasks/<seq>-<topic>/poc-report.md`)
- ADR (채택·기각 모두 ADR로 영구화)

## 금지
- PoC 코드를 그대로 main에 merge
- 시간 박스 무시
- 측정 없이 "느낌"으로 결론
- 결정 책임자/기한 누락
- PoC 중 secret commit (시간 박스라도 보안 절대)
- ADR 없이 결정 종료 (구두 합의 X)
- PoC 결과를 다음 PoC가 인용 못하도록 정리 안 함 (report 의무)

## 참고
- 결정 일반은 `git/issue.md` decision type
- ADR 형식은 `docs/ard.md`
- 측정·관찰 가능성은 `observability/observability.md`
