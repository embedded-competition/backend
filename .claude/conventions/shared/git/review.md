---
name: shared-git-review
description: PR을 코드 리뷰하거나 리뷰 코멘트·승인 정책을 적용할 때 사용한다.
---

## Rule
- 모든 PR은 merge 전 1+ 리뷰 승인 + CI green + CODEOWNERS 매칭 필요. 1인 프로젝트면 self-review 허용 (단 24h 쿨다운 또는 의식적 재읽기).
- 리뷰어는 다음 6 축을 확인한다:
  - **도메인 일관성**: glossary 어휘 준수, ADR 결정 부합, layer 경계(architecture/*.md) 준수
  - **테스트**: 추가/변경된 동작에 Karate feature 또는 단위 테스트 동반. 외부 동작 변경에 시나리오 없으면 reject
  - **convention 준수**: cleancode/oop/architecture md 위반 없는지 (else 금지, getter/setter 금지, 함수 ≤ 20줄 등)
  - **migration 안전성**: Flyway 1 PR 1 migration, DDL/백필 분리, Expand-Contract 두 단계 배포 가능
  - **secret/leak**: 비밀값·내부 URL·credential 노출 없음
  - **observability**: 로그·메트릭·예외 매핑이 도메인 예외 → HTTP status 일관
- 리뷰 코멘트 prefix 표기:
  - `nit:` — 사소한 스타일 (block X)
  - `q:` — 질문/확인 (block X)
  - `suggest:` — 개선 제안 (author 판단)
  - `blocker:` — 머지 차단 (해결 필요)
- 응답 시간: author는 24h 내 코멘트 응답 권장. blocker 미해결 시 merge X.
- 리뷰어는 자기가 author인 코드 self-approve 금지 (1인 프로젝트의 self-review는 별도 — 시간차 + 재읽기로 의식 분리).
- 큰 PR(> 400 LOC)은 1차 리뷰에서 분할 요청 가능.
- 보안 영향 큰 변경(auth/secret/exception handler/migration)은 추가 리뷰어 1명 또는 보안 owner 매칭.
- approval 후 author가 force-push로 변경하면 re-review 필요 (`stale review` 정책 branch protection 활성).

## Anti-pattern
- "LGTM" 한 마디 후 무조건 approve (6 축 미확인)
- blocker 미해결 채 merge
- self-approval (1인 self-review는 시간차 필수)
- CI fail 상태 merge 강행 (`--admin` 또는 force-merge)
- approval 후 코드 변경 + re-review 없이 merge (stale review)
- 무리뷰 hotfix를 사후 PR 정당화 (긴급 정책 별도)
- 리뷰 코멘트에 인신공격 (코드 비판은 OK, 사람 비판 X)
- 외부 라이브러리 추가/major bump를 review 없이 통과
- migration PR을 일반 PR과 같은 리뷰 강도로 (DB 변경은 더 엄격)
- 무관한 변경 요구 (scope creep — 별 PR로)
