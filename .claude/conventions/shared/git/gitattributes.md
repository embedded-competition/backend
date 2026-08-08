---
name: shared-git-gitattributes
description: .gitattributes로 EOL·binary·linguist·merge driver를 설정할 때 적용한다.
---

## Rule
- `.gitattributes`로 EOL·binary·linguist·merge driver를 통일한다.
- EOL 정책: `* text=auto eol=lf` 기본. Linux 기준 LF 통일. Windows 협업해도 checkout 시 자동 변환.
- shell script는 명시 LF: `*.sh text eol=lf`.
- Windows 전용 파일이 있다면 `*.bat text eol=crlf`, `*.cmd text eol=crlf`.
- binary 파일은 명시 binary: `*.png binary`, `*.jpg binary`, `*.jar binary`, `*.db binary`, `*.pdf binary`. diff 시도하지 않음.
- linguist 힌트로 GitHub 언어 통계 정확화:
  - 생성 코드: `**/generated/** linguist-generated=true`
  - vendored: `python/legacy_backend/** linguist-vendored=true` (예시)
  - 문서: `docs/** linguist-documentation=true`
- 머지 driver:
  - lock 파일은 union merge로 conflict 줄이기: `*.lock merge=union`, `uv.lock merge=union`, `package-lock.json merge=union`
  - 일부 yml은 union 가능하지만 의미 충돌 risk 있어 신중
- LFS 도입 시: `*.weights filter=lfs diff=lfs merge=lfs -text`, `*.pth filter=lfs ...`
- `.gitattributes`는 repo root에 두기. sub-dir별 attributes는 sub-dir의 `.gitattributes` 추가.
- 변경 시 PR description에 영향 범위 명시 (EOL 정책 변경은 diff 폭증 위험).

## Anti-pattern
- EOL 정책 누락 (host별 LF/CRLF 혼재 → diff 노이즈)
- 큰 binary를 text로 두기 (diff 무의미 + repo 부피)
- `text=auto`만 두고 명시 binary 누락 (binary가 text로 변환되어 손상)
- linguist 힌트 누락한 채 generated/vendored 코드 commit (언어 통계 왜곡)
- LFS 도입 후 `.gitattributes` 누락 (filter 작동 안 함)
- attributes 충돌 (한 패턴에 모순된 속성)
- attributes 변경 후 `git add --renormalize .` 누락 (기존 파일에 적용 안 됨)
- 임의 머지 driver 사용으로 의미 변경 (semantic conflict 가림)
