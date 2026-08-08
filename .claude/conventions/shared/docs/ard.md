---
name: shared-docs-ard
description: 아키텍처 결정(ADR)을 기록·변경·역참조할 때 적용한다. ADR은 마크다운 파일이 아니라 empty commit으로 남긴다.
---

## Rule
- ADR(Architecture Decision Record)은 **empty commit으로 남긴다** (`git commit --allow-empty`). 마크다운 파일·`docs/decisions/`·CLAUDE.md 인덱스를 만들지 않는다.
- subject: `adr(<scope>): <NNNN> <한 줄 결정 요약>` (NNNN = 4자리 zero-pad, 단조 증가).
- body(전문, WHY가 핵심):
  - `Context`: 결정이 필요해진 배경·제약·트레이드오프
  - `Decision`: 채택한 안 (1~3문장)
  - `Consequences`: 따라오는 변화·비용·후속 작업
  - `Alternatives`: 검토 후 기각한 안과 기각 이유
- trailer: `ADR: <NNNN>-<kebab-slug>` (인덱스 키). `Agent:`, `Feature:` 동반.
- ADR은 결정이 **발생한 phase·주체**로 남긴다 — plan 단계 결정 → `Phase: plan`/`Agent: <plan 주체>`, build 중 결정 → `Phase: build`/`Agent: <build 주체>`. 고정 phase에 묶지 않는다.
- 1 ADR = 1 결정. 여러 결정 묶기 금지. 번호 단조 증가, 재사용·건너뛰기 금지.
- 결정 변경 시 기존 ADR 커밋을 수정하지 않고 **새 ADR empty commit 작성** + trailer `Supersedes: <NNNN>-<slug>`.
- 조회·인덱스 = `git log --grep="^ADR:"` (slug로 읽힘). 별도 인덱스 파일 불필요.
- squash landing 시 ADR 커밋 전문을 squash 본문에 carry (영속).
- 결정에 영향받는 코드/커밋에 ADR id로 역참조 (`ADR: <NNNN>-<slug>` trailer).

## Anti-pattern
- ADR을 마크다운 파일로 작성 (empty commit으로 해야 함)
- 같은 ADR을 후속 수정으로 의미 변경 (새 ADR + `Supersedes`)
- 1 ADR에 여러 결정 묶기
- 번호 재사용/건너뛰기
- "이렇게 했다" 식 WHAT 위주 기술 (WHY 필수)
- Alternatives 섹션 생략 (대안 검토 흔적 없는 결정 = 근거 부족)
- trailer 값에 slug 없이 맨 번호
- squash 시 ADR 전문 carry 누락 (결정 근거 소실)
- ADR 본질 결정(layer/persistence/communication 등)을 ADR 없이 진행
