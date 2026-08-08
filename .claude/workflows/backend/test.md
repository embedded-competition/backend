---
name: backend-test
description: 테스트를 작성·실행·관리할 때 따르는 절차. 단위(JUnit5)와 통합(Karate) 2층 구조.
---
## 목적
테스트 작성·실행·관리 절차. 단위(JUnit5)와 통합(Karate) 2층 구조.

## 테스트 층
| 층 | 도구 | 위치 | 책임 |
|---|---|---|---|
| 단위 | JUnit5 + AssertJ | `src/test/java/.../<package mirror>/<Class>Test.java` | 도메인 객체 행위·invariant, UseCase 조율, VO 생성 검증 |
| 통합/E2E | Karate | `src/test/resources/karate/<context>/<usecase>.feature` | 외부 동작 명세, HTTP 진입 → 응답 검증 |

`@SpringBootTest` 신규 통합 테스트 작성 X (Karate가 대체 — ADR-004).

## 작성 순서 (outside-in)
1. Karate feature 1개 작성 (red)
2. 도메인 단위 테스트 작성 (도메인 invariant·VO 검증)
3. UseCase 단위 테스트 작성 (port mock — adapter만)
4. 구현 → 둘 다 green

## 단위 테스트 룰 (framework/junit.md)
- 한 테스트 = 한 시나리오
- given/when/then 구조
- 모킹 최소(외부 경계만)
- 도메인 객체 mock 금지
- 테스트 간 독립 (공유 상태 X)
- 시간 의존은 `Clock` 주입

## Karate 룰 (framework/karate.md)
- API 호출로 fixture 셋업 (DB·파일 직접 X)
- schema 검증 우선
- 시나리오 독립
- tag 분류 (`@smoke`, `@e2e`)

## 실행
- 단위: `./gradlew test`
- Karate: `./gradlew karateTest`
- 둘 다: `./gradlew check`

## CI 게이트
- PR: 단위 + Karate 모두 green 필수 (`workflows/cicd.md`)
- fail 시 PR merge X

## 변경별 테스트 동반
| 변경 | 동반 테스트 |
|---|---|
| 새 UseCase | Karate 시나리오 1+ + UseCase 단위 테스트 |
| 도메인 invariant 추가 | VO/Aggregate 단위 테스트 |
| Repository 메서드 추가 | UseCase 통해 Karate에서 검증 (Repository 직접 테스트 보통 안 함) |
| Bug fix | 회귀 테스트 1개 + Karate 시나리오 (재발 방지) |
| Refactor | 기존 테스트 green 유지. 새 테스트 추가 X |
| Migration | Karate 시나리오에 이전·이후 동작 검증 |

## 안티패턴
- assertion 없는 테스트
- `@Disabled` 누적 (이유·해결 책임자 없이)
- Thread.sleep
- 외부 자원 직접 의존 (실제 DB·네트워크) — 단위 테스트에서
- 같은 시나리오를 단위 + Karate 둘 다 (중복)
- random seed 없이 random
- 테스트 안 비밀값 hardcode
