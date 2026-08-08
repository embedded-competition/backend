---
name: shared-git-gitignore
description: .gitignore를 작성하거나 파일의 git 추적 여부를 결정할 때 적용한다.
---

## Rule
- `.gitignore`는 카테고리별로 섹션을 나눠 가독성을 유지한다. (VCS / build / IDE / OS / secret / cache / data)
- 추적 여부 결정 기준 4축:
  - **크기**: 단일 파일 > 50MB 이면 LFS 또는 외부 storage 검토. > 500MB 이면 git 추적 금지
  - **변경 빈도**: 자주 변경(코드) = git. 거의 안 변경(deps·model) = image/storage
  - **출처**: 우리가 작성(IP) = git. 외부 retrievable(URL/registry) = Dockerfile/base image
  - **추적 필요성**: diff 의미 있음(텍스트) = git. binary diff 무의미 = image/storage
- **secret 카테고리는 무조건 ignore**:
  - `.env`, `.env.*`, `!.env.example`
  - `*.pem`, `*.key`, `*.p12`, `*.pfx`
  - `credentials*.json`, `*credentials*.yml`
  - `**/secrets/`, `**/private/`
  - `application-local.yml` (DB password 포함 가능)
- 빌드 산출물: `build/`, `out/`, `target/`, `dist/`, `*.jar`(wrapper 제외)
- 캐시: `.gradle/`, `.cache/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`, `**/__pycache__/`, `*.py[cod]`
- IDE/편집기: `.idea/`, `.vscode/`, `*.iml`, `*.swp`, `*.swo`
- OS: `.DS_Store`, `Thumbs.db`
- runtime data: `var/`, `logs/`, `tmp/`, `backups/*.{tar.gz,tgz,zip}`
- 큰 binary/model: `*.pth`, `*.pt`, `*.onnx`, `*.ckpt`, `*.weights`, `*.h5`, `*.npz` (LFS or 외부 storage)
- `.env.example`은 commit (키 목록 공유). allowlist는 `!` prefix.
- 새 카테고리 추가 시 코멘트로 섹션 명시. PR description에 이유 명시.
- 추적 중인 파일을 ignore에 추가하면 `git rm --cached <path>` 따로 실행 + commit.

## Anti-pattern
- secret 카테고리 누락 (`.env`, `*.pem`, `*.key`, `credentials*` 등)
- 전체 무시(`*`) 후 allowlist만 (의도 추적 어려움)
- `.gitignore` 자체를 ignore (역설)
- 이미 commit된 secret을 ignore만 추가하고 history 정리 누락 (`git filter-repo` 또는 BFG로 history 제거 필요)
- 50MB+ binary를 별 검토 없이 commit
- ML model weights, dataset을 git에 직접 commit
- IDE 메타 파일을 무시 안 한 채 commit (host별 노이즈)
- 빌드 산출물을 git에 commit (재현성 깨짐)
- 카테고리 섹션 없이 무질서한 한 줄씩 추가

## 자산 위치 결정 트리
```
사람이 작성한 텍스트?         → git
외부 build에서 retrieve 가능? → Dockerfile RUN install
자주 안 변하고 무거운 deps?   → custom base image
50MB+ binary, 추적 필요?      → Git LFS
50MB+, 추적 불필요?           → S3/GCS + download script
런타임 생성 데이터?           → runtime volume (compose volumes)
비밀값?                       → secret manager / env (git X)
```
