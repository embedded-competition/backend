---
name: shared-code-review
description: PR 머지 전 6축(도메인·테스트·convention·migration·secret·observability) 코드 검토를 수행할 때 사용.
---
## 목적
PR 머지 전 6축 검토 절차. `git/review.md` 정책을 실행 단계로 풀어둠.

## 검토 6 축 (git/review.md와 짝)
1. **도메인 일관성**: glossary 어휘 준수, ADR 부합, layer 경계 준수
2. **테스트**: 동작 변경에 Karate/JUnit 동반. 회귀 테스트 포함
3. **convention 준수**: code/architecture/framework/* 위반 없음
4. **migration 안전성**: 1 PR 1 migration, Expand-Contract 분리
5. **secret/leak**: 비밀값·내부 URL·credential 노출 없음
6. **observability**: 로그·메트릭·예외 매핑 일관

## 절차
1. **자기 검토 (author, PR open 직전)**
   - 6 축 self-check
   - PR description 6 axis 채움 (`.github/pull_request_template.md`)
   - draft → ready for review 전환
2. **자동 검사 (CI)**
   - lint + test + Karate (workflows/cicd.md)
   - secret scan (gitleaks)
   - 의존성 보안 스캔
3. **리뷰어 검토 (1+ approval)**
   - 6 축 확인 (이상 순서로)
   - 코멘트 prefix: `nit:` / `q:` / `suggest:` / `blocker:`
   - blocker 미해결 시 merge X
4. **author 응답** (24h 권장)
   - blocker는 코드 수정 또는 토론 후 합의
   - suggest는 author 판단
   - 변경 push 후 reviewer ping
5. **stale review 재검토**
   - approval 후 force-push 발생 시 자동 stale 표시. re-review 필요
6. **merge**
   - CI green + 1+ approval + blocker 0 + CODEOWNERS 매칭 → squash merge

## 변경 종류별 추가 검토
| 변경 | 추가 검토 |
|---|---|
| migration | DBA 또는 backend 시니어 1명 추가 (framework/flyway.md Expand-Contract 검증) |
| auth/secret | security owner 추가 (security/security.md) |
| ADR 결정 | architect 추가 |
| 외부 라이브러리 추가 | 라이선스·취약점·필요성 검토 (build/dependencies.md) |
| Dockerfile / compose | infra owner |
| .github/workflows | CI/CD owner |

## 1인 프로젝트 self-review
- author self-approval 금지
- 24h 쿨다운 후 의식적 재읽기
- 그래도 self-merge할 거면 6 axis 체크리스트 PR comment로 남김
- 추후 협업자 추가 시 일반 절차로 전환

## 안티패턴
- "LGTM" 한 마디 후 무조건 approve
- blocker 미해결 머지
- approval 후 코드 변경 + re-review 없이 머지
- 무관한 scope creep 요구 (별 PR로)
- 인신공격 (코드 비판 OK, 사람 비판 X)
- CI fail 우회 (`--admin` 머지)
