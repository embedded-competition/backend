---
name: shared-git-branch
description: Git 브랜치를 생성·명명·분기·머지·삭제할 때 적용한다.
---

## Rule
- GitHub Flow 채택. 장기 브랜치는 `main` 1개.
- 작업 브랜치는 `<type>/<short-topic>` 명명. (`feat/map-polygon-binding`, `fix/scan-timeout`, `refactor/floor-usecase-split`)
- type prefix는 Conventional Commits와 일치: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `build`, `ci`, `perf`.
- topic은 kebab-case, ≤ 5 단어.
- 브랜치 1개 = task 1개 = PR 1개. cross-task 묶음 금지.
- 브랜치는 `main`에서 분기. 다른 feature 브랜치에서 분기 금지 (의존 브랜치).
- merge 방식은 **squash merge**. landing 시 fast-forward 깔끔.
- merge 후 브랜치는 즉시 삭제 (remote + local).
- 장수 브랜치(2주 초과)는 main에 rebase로 동기화.
- 실험/스파이크는 `spike/<topic>`. merge 안 함, 결과만 ADR로.

## Anti-pattern
- `main` 직접 push (PR 경유)
- 다른 feature 브랜치에서 분기 (의존 chain)
- 브랜치 1개에 무관한 변경 묶기
- 한글/공백/특수문자 포함 브랜치명
- `master`, `develop`, `release/*` 같은 GitFlow 잔재 명명
- merge commit 사용 (squash merge 통일)
- merge 후 브랜치 방치
- `--force` push to `main` (어떤 이유든 금지)
- `--no-verify`로 hook skip
