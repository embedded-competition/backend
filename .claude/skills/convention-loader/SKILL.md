---
name: convention-loader
description: 코드를 작성·수정·리뷰하기 직전, 현재 작업에 해당하는 규칙(컨벤션)만 골라 컨텍스트에 주입할 때 사용. "규칙을 로드한다", "이 작업에 해당하는 규칙 로드", "관련 컨벤션 로드", "이 작업 규칙 가져와", "적용할 컨벤션 확인", "convention 매칭" 트리거. conventions 디렉토리 전체를 통째로 읽지 않고 frontmatter description만 스캔해 매칭된 것만 본문 로드한다.
---

# convention-loader

## Purpose
현재 작업에 필요한 컨벤션만 동적 선별해 주입. 전체 로드는 토큰 낭비 + 무관 규칙 noise. frontmatter(description)만 1차 스캔 → 의미 매칭 → 매칭분만 본문 로드.

## Inputs
- `conventions_dir` — 컨벤션 자산 디렉토리(탐색 대상). 호출자가 지정. 미지정 시 프로젝트 설정에서 자산 경로 확인.
- 현재 작업 설명 (무엇을 작성·수정·리뷰하는지).

## Procedure
1. **스캔 (deterministic)**: `bash {skill_dir}/scripts/list-frontmatter.sh {conventions_dir}`. name·description만 나오고 본문은 안 읽는다 (토큰 절약).
2. **매칭**: 현재 작업 설명 ↔ 각 description을 의미 매칭. 키워드 일치가 아니라 "이 작업에 이 규칙이 적용되는가"로 판단.
3. **분기**: 매칭 결과로 갈린다 (Flow 참고).
4. 매칭된 컨벤션만 본문 전체를 Read 해 컨텍스트에 주입.
5. 적용한 컨벤션 name 목록 보고.

## Flow
- list-frontmatter 스캔 → 의미 매칭.
- 매칭 0개 → "해당 컨벤션 없음" 보고 후 그대로 진행.
- 매칭 1개+ → 매칭분 본문 Read·주입 → 적용 name 보고.

## Constraints
- 탐색 디렉토리를 하드코딩하지 않는다 — 입력으로 받는다.
- 전체 컨벤션 본문을 로드하지 않는다 — 매칭된 것만 본문 읽는다.
- 매칭 0개인데 추측으로 아무거나 로드하지 않는다 — 0개면 "해당 컨벤션 없음" 보고 후 그대로 진행.
- 호출자가 skill 이름을 박아야 발동된다고 가정하지 않는다 — 추상 의도 발화 + description 매칭으로 자동 발동된다 (호출자가 `Skill` 도구 보유 시).
