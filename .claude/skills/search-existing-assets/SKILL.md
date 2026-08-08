---
name: search-existing-assets
description: |
  코드/ADR/TODOS/project-map 4 영역 통합 조회. 사용자 pain "이전 자산 못 찾고 새로 만듦" 차단.
  트리거: "기존 자산", "이미 있는지", "search-existing", "관련 ADR", "이전에 한 거", "중복 확인", "project-map", "TODOS grep", "이전 결정", "전에 만든 거", "이미 구현돼 있나".
  비-트리거: 새 자산 작성(save-decision), 단발 grep(Bash 직접), 외부 라이브러리 검색(WebSearch).
inputs:
  - "query_text: 자연어 또는 키워드 (필수)"
  - "scopes: [code, adr, todos, project_map] (default: 모두)"
  - "task_context: 현재 task 설명 (선택)"
outputs:
  - "matches: {code, adr, todos, project_map}"
  - "summary: 발견 항목 한 줄 요약"
triggers:
  - 기존 자산
  - 이미 있는지
  - search-existing
  - 관련 ADR
  - 이전 결정
  - 중복 확인
  - project-map grep
not_for:
  - 새 자산 작성 (save-decision)
  - 단발 grep (Bash 직접)
  - 외부 라이브러리/패키지 검색 (WebSearch)
---

# search-existing-assets

4 영역 (코드, ADR, TODOS, project-map)을 병렬 조회해 관련 기존 자산을 보고한다. 읽기 전용 — 변경 없음.

## 사용 시점

- `git-workflow` branch 생성 직후 자동 호출
- `build-<lang>-<framework>-<domain>` 계열 step 1 영향 범위 조사
- eval-adr-conformance 호환성 사전 조회
- 사용자가 "이미 만든 거 있어?" 류의 질문 시

## 절차

### Step 1: code 스코프

```bash
# 키워드 grep (함수명, 모듈명, 파일명)
grep -r "<query_text>" <project>/ --include="*.md" --include="*.py" --include="*.ts" --include="*.swift" -l
grep -r "<query_text>" <project>/agents/ <project>/skills/ -l 2>/dev/null
```

### Step 2: ADR 스코프

```bash
# docs/decisions/ 존재 시
ls <project>/docs/decisions/*.md 2>/dev/null
grep -l "<query_text>" <project>/docs/decisions/*.md 2>/dev/null
# 각 match: frontmatter status + Decision 섹션 첫 줄 추출
```

부재 시: 빈 결과 + "docs/decisions/ 없음" warning

### Step 3: TODOS 스코프

```bash
grep -n "<query_text>" <project>/TODOS.md 2>/dev/null
# priority(P0-P4), what, Depends on 파싱
```

부재 시: 빈 결과

### Step 4: project-map 스코프

```bash
grep -n "<query_text>" <project>/docs/project-map.md 2>/dev/null
# module, responsibility, entry_point 파싱
```

부재 시: 빈 결과 + "project-map.md 없음" warning

### Step 5: 보고

```
search-existing-assets 결과:
- 코드: <N>개 파일 (예: agents/build/`build-<lang>-<framework>-<domain>` 계열.md:42)
- ADR: <N>개 (예: 0001-capability-refactor, status:draft)
- TODOS: <N>개 (예: P2: worktree dogfood)
- project-map: <N>개 모듈
요약: <한 줄>
```

관련 자산 발견 시 사용자에게 재사용 권장. 동일 기능 발견 시 재구현 차단 경고.

## 필수 artifact

보고 텍스트 (변경 파일 없음 — 읽기 전용)

## 오류 처리

- `docs/decisions/` 부재: 빈 결과 + warning (중단 아님)
- `docs/project-map.md` 부재: 빈 결과 + warning (중단 아님)
- `TODOS.md` 부재: 빈 결과 (중단 아님)
