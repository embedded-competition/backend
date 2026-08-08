---
name: shared-code-oop
description: 객체지향 도메인 코드(클래스·엔티티·VO·메서드)를 작성·리뷰할 때 적용
---

## Rule (객체지향 생활체조 9 + 이 프로젝트 추가)
- 메서드당 들여쓰기 1단계. 중첩 시 추출.
- `else` 금지. 가드 클로즈로 early return.
- 원시값과 문자열은 포장 (VO). primitive obsession 차단.
- 일급 컬렉션 사용. `List<X>`를 직접 노출 말고 `Xs` 같은 컬렉션 VO로 감쌈.
- 한 줄에 점 하나 (Law of Demeter). `a.b().c().d()` 금지.
- 축약 금지 (cleancode.md와 공유).
- 엔티티 작게 유지. 인스턴스 변수 ≤ 3. public 메서드 ≤ 5.
- getter/setter 금지. 객체는 자기 데이터를 외부에 노출하지 않는다.
- 선언형 프로그래밍 우선. 상태 변경보다 변환·합성.

## Tell Don't Ask
- 객체에 묻지 말고 시킨다. getter로 값 꺼내 외부에서 분기 X.
- 비즈니스 로직은 그 데이터를 가진 객체 안으로.
- 예시:
  - ❌ `if (order.getStatus() == CANCELED) ...`
  - ✅ `order.ifCanceled(action)` 또는 `order.cancel()`이 invariant 검증
- 객체의 행위(메서드)가 객체의 상태(필드)보다 풍부해야 한다.

## Early Return / Guard Clause
- 비정상 경로를 함수 진입부에서 먼저 차단한다.
- 정상 경로의 들여쓰기를 깊게 만들지 않는다.
- `else` 사용 금지 — 분기는 가드로 분해.
- 예시:
  - ❌ `if (valid) { ... do work ... } else { throw ... }`
  - ✅ `if (!valid) throw ...; do work;`

## Null Object / Optional
- null 반환 금지. Optional 또는 Null Object 패턴.
- null 파라미터 금지. `@NonNull` 명시 또는 Optional.
- 컬렉션은 빈 컬렉션 반환. null 반환 X.
- Optional은 반환 타입 한정. 필드/파라미터에 Optional 사용 지양.
- Null Object 패턴: 도메인에 "없음" 의미가 자주 등장하면 NullX 구현체로 분기 제거.

## 선언형 우선
- stream/map/filter/collect 같은 변환 합성 우선.
- 명령형 for 루프는 부수효과(`add`, `update`)가 있을 때 한정.
- 가독성 떨어지는 stream chain은 메서드 추출.

## Anti-pattern
- `else` 사용
- getter/setter (Lombok `@Getter`/`@Setter`/`@Data` 포함)
- 한 줄에 점 2개 이상 (Law of Demeter 위반)
- 메서드 들여쓰기 2단계 이상 (1단계 원칙. 1~2단계까지 점진 허용 가능, 3단계 이상 금지)
- 원시값(`String`/`Long`)으로 식별자/측정값 표현
- 일급 컬렉션 없이 `List<X>` 직접 도메인 경계 노출
- `Util`/`Helper`로 비즈니스 규칙 빼기
- null 반환/전달
- 도메인 객체에 행위 없이 getter만 (anemic domain model)
- `if-else` 사다리 (가드/early return으로 분해 또는 strategy로)
