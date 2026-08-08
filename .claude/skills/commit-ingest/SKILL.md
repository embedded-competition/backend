---
name: commit-ingest
description: 커밋 로그를 읽어 deprecated·superseded를 거른 압축 프로젝트 컨텍스트를 만들 때 사용. /clear·/compact 후 컨텍스트 복원, 작업 시작 전 현재 살아있는 결정·피처 파악. "프로젝트 컨텍스트 채워", "커밋 로그 ingest", "현재 결정 뭐가 살아있어", "지금 프로젝트 상태", "컨텍스트 복원" 트리거. 비-트리거 — 커밋 생성(git-commit 절차), 자산 검색, worktree 상태 확인.
---

# commit-ingest

## Purpose
- main 커밋 로그에서 살아있는(deprecated·superseded 제외) 결정·피처만 압축 추출해 프로젝트 컨텍스트를 채운다.
- 매번 전체 로그를 읽는 컨텍스트 혼동·버전 혼동을 차단한다.

## Inputs
- `ref` — 읽을 branch (기본 main).

## Workflow

### s0 Validate input — precondition
- cwd가 git repo인지 확인.
- 충족 → s1
- 아니면 호출자에 반환 (outcome = needs-input)

### s1 Ingest
- `bash {skill_dir}/scripts/ingest-commit-log.sh <ref>` 실행 (결정적).
- 출력 = live ADR + live feature + deprecated 카운트.

### s2 Inject
- 출력을 현재 컨텍스트에 프로젝트 상태로 주입한다.
- 특정 결정·피처의 전문이 필요하면 해당 커밋을 on-demand 조회한다 (`git log --grep`, `git show`).

## Constraints
- deprecated·superseded는 컨텍스트에 올리지 않는다 — 버전 혼동 차단.
- 전체 커밋 전문을 주입하지 않는다 — 압축 live 뷰만, 전문은 on-demand.
- 추론으로 deprecated 판정하지 않는다 — `Deprecates`·`Supersedes` trailer만 신뢰.
