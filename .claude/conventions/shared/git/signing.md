---
name: shared-git-signing
description: commit·tag에 서명을 적용하고 signing key를 관리할 때 사용한다.
---

## Rule
- 모든 main 브랜치 commit과 SemVer tag는 signed. branch protection에서 "Require signed commits" 활성.
- signing 방식은 **SSH key 권장** (GPG보다 관리 단순). GPG도 허용.
- 개발자는 GitHub 계정에 signing key 등록. expire 갱신 정책: 1년 단위.
- local git 설정:
  ```
  git config --global commit.gpgsign true
  git config --global tag.gpgsign true
  git config --global gpg.format ssh
  git config --global user.signingkey <key-path-or-id>
  ```
- CI/bot이 만드는 commit·tag도 sign 한다 (machine identity). GitHub Actions의 경우 GPG action 또는 GitHub App token 사용.
- merge 전 GitHub UI에서 "Verified" 배지 확인. unverified는 reject.
- signing key는 personal credential — 공유 금지. expire 시 새 키 발급 + 이전 키 revoke.
- tag (release.md `vX.Y.Z`)는 annotated + signed (`git tag -s vX.Y.Z`).
- commit author와 signing key의 email은 일치시킨다 (impersonation 차단).

## Anti-pattern
- unverified commit이 main에 진입 (branch protection으로 강제)
- signing key를 repo에 commit
- 만료된 key 사용 (expire 후 즉시 갱신)
- CI/bot이 unsigned commit 생성
- `--no-gpg-sign` 우회
- 다른 사람 key로 sign (impersonation)
- key 분실 후 revoke 누락 (계속 신뢰 상태)
- 같은 commit을 여러 key로 sign (혼동)
- SemVer tag를 lightweight (`git tag vX.Y.Z`)로 생성 (annotated + signed만)
