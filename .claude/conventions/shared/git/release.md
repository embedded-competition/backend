---
name: shared-git-release
description: SemVer 버전 태그를 찍어 릴리스·배포·롤백할 때 적용한다.
---

## Rule
- 버전은 SemVer (`vMAJOR.MINOR.PATCH`). 태그 형식 `vX.Y.Z` (예: `v0.3.1`).
- main에 PR squash merge → `dev` 환경 자동 배포 (registry image digest 기반).
- prod 배포는 main에 SemVer 태그 push로 trigger. dev에서 검증된 같은 digest를 prod로 promote.
- changelog는 `CHANGELOG.md`에 release-please 또는 conventional-commits 기반 자동 생성.
- breaking change는 MAJOR bump. footer `BREAKING CHANGE:` 또는 type 뒤 `!` (`feat!:`).
- pre-release는 `vX.Y.Z-rc.N` 형식. prod tag와 분리.
- hotfix는 main에서 분기 → 빠른 PR → 태그 bump → 배포. 별도 long-lived branch 없음.
- 롤백은 이전 SemVer 태그를 다시 promote (image digest 기반이라 즉시 가능).
- 태그 push는 GitHub Actions가 trigger. 수동 배포 명령 금지 (재현 불가).
- release note는 자동 생성 본문 + 사람이 검수 후 publish.

## Anti-pattern
- 태그 형식 비표준 (`release-2024`, `v1`, `1.0` 등)
- 같은 SemVer 태그 재사용 (immutable)
- main 외 branch에 prod 태그
- 태그 push 후 코드 변경 (재태그 X — 새 PATCH로 새 태그)
- 수동 docker push로 prod 배포
- changelog 누락한 채 태그 push (자동 생성 안 되면 PR에서 보강)
- registry image 재빌드로 promote (dev 검증 digest와 다른 binary가 prod에 가면 검증 무의미)
- pre-release 태그를 prod로 promote
- hotfix를 main 우회 (모든 변경은 main 경유)
- `--force` tag push
