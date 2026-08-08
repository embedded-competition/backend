---
name: shared-git-hooks
description: pre-commit·pre-push 같은 git hook을 정의·설치할 때 적용한다.
---

## Rule
- pre-commit hook은 빠른 정적 검증만 (spotless, secret scan, conventional-commits subject lint).
- pre-push hook은 약간 더 무거운 검증 (unit test 한정, e2e/Karate는 CI에 위임).
- hook 관리는 **client-side 자동 설치 가능한 방식** 사용. (lefthook / pre-commit framework / gradle git-hooks plugin 중 택1)
- hook 정의는 repo 추적 파일 (`lefthook.yml` 또는 `.pre-commit-config.yaml`). `.git/hooks/`만 의존 금지 (clone 시 사라짐).
- hook 실행은 1초 미만 목표 (commit 끊김 방지). 1초 초과 항목은 pre-push로 이동.
- spotless 자동 포맷은 pre-commit에서 `applyAndStage` 대신 `check` 권장. 사람이 의도적으로 format 실행 후 stage.
- secret scan은 `git-secrets` 또는 `gitleaks` 사용. 평문 토큰 commit 차단.
- hook 실패 시 `--no-verify` 우회 금지 (commit.md forbidden).
- 새 hook 추가 시 PR description + 팀 공지.

## Anti-pattern
- `.git/hooks/`만 의존 (untracked, clone 후 자동 적용 X)
- pre-commit에 e2e/통합테스트 (CI로)
- hook 안 외부 네트워크 호출 (offline 깨짐)
- hook 안 비밀값 처리
- 1 hook에 무관한 검증 묶기
- hook 실패 silent skip (시각화 필수)
- `--no-verify` 우회
- pre-commit 1초 초과 (개발 흐름 차단)
