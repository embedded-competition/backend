---
name: shared-eval
description: 변경분이 합의된 계획·완료기준을 충족하고 회귀가 없는지 판정해 Verdict를 낼 때 따르는 절차. read-only — 수정하지 않는다. 사용자 최종 승인은 상위.
---

## When
- 구현 후, 변경분이 합의된 계획·완료기준을 충족하고 회귀가 없는지 판정할 때.

## Inputs
- 변경분: diff·대상.
- 합의된 계획·완료 기준(acceptance).
- live 컨텍스트: 현재 살아있는 결정 (위반 검사용).

## Steps
1. 판정 기준 규칙을 로드한다.
2. 완료기준 충족 여부를 항목별로 확인한다.
3. 빌드·테스트를 실행해 회귀를 본다 (실행만, 수정 금지).
4. 로드된 규칙·살아있는 결정 위반을 확인한다.
5. Verdict를 낸다 — 전 기준 충족·회귀 없음 → pass / 일부 미충족·보완 가능 → needs-changes / 본질 미충족·회귀 → fail. 근거 동반.

## Outputs
- Verdict: pass | fail | needs-changes.
- 기준별 근거: 충족·미충족 항목, 회귀·규칙 위반 증거.
- 코드·테스트 미수정.

## Handoff
- 코드·테스트 수정 → build 절차.
- 계획 작성 → plan 절차.
- 사용자 최종 승인(검증 게이트), Verdict의 커밋 기록 → 상위(harness).
