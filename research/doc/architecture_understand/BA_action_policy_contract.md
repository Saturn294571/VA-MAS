# BA/Minecraft Agent 행동 선택 계약 초안

상태: **기존 생성형 경로의 계약 어댑터 구현**. [`env/action_policy.py`](../../../env/action_policy.py)에 입력·출력 형식, 공통 검증기와 기존 ReAct 도구 래퍼가 있다. `ActionPolicy.select()`를 사용하는 독립적인 1회 결정 루프와 결정형 정책은 아직 구현되지 않았다. 목적은 VA의 동일한 작업·관측·도구 제약 아래에서 생성형(G)과 결정형(D)의 **다음 행동 선택**을 비교하는 것이다. BA의 작업 완료 판단, Controller의 배정, Minecraft 실행기와 benchmark judger는 이 계약의 책임이 아니다.

## 1. 실제 코드의 경계

| 단계 | 현재 경로 | 계약에서의 위치 |
| --- | --- | --- |
| 작업 수신·문맥 구성 | [`BaseAgent.step()`](../../../pipeline/agent.py) → `normal_step()`이 `Task` 설명·milestones, Data Manager의 환경·이력, 동료 상태를 프롬프트로 구성 | 공통 입력 구성. 정책별 정보량을 달리하지 않음 |
| 실행 요청 | `BaseAgent.normal_step()` → [`VillagerBench.step()`](../../../env/env.py) → [`Agent.run()`](../../../env/minecraft_client.py) | BA 바깥의 호출·반환 경계 유지 |
| 행동 결정 | `Agent.run()`이 `STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION` 에이전트를 만들어 `self.tools` 중 도구와 인자를 생성 | **교체 대상**: 한 시점의 도구·인자 선택 |
| 행동 실행·관측 | LangChain 에이전트가 도구를 실행하고 `intermediate_steps`에 행동·피드백을 남김 | 공통 실행기·관측 수집. 선택 결과를 검증한 뒤 실행 |
| 완료·피드백 | `Agent.run()`의 `final_answer`와 `action_list` → BA의 DB 갱신·`reflect()` → Controller; 별도 judger | 정책이 완료 점수나 reflection을 직접 결정하지 않음 |

현재 `Agent.run()`은 여러 ReAct 단계를 **한 번에** 실행한다. 기존 호출·최종 반환 형식을 유지하면서 각 도구 호출 앞에 계약 검증기를 감쌌고, `action_contract`를 `detail`에 추가했다. 따라서 도구의 인자 형식·agent 일치·허용 목록은 실행 전에 검사하지만, LangChain 내부의 도구 선택 자체는 여전히 생성형 ReAct가 수행한다. 알 수 없는 도구와 파서 오류는 래퍼 밖에서 처리될 수 있으므로 사후 기록을 구분한다. `Agent.step()`/`VillagerBench.iter_step()`에도 동일 기록을 적용했으나 현재 주 실행 경로인 `BaseAgent.normal_step()`은 `Agent.run()`을 사용한다. 이 두 경로를 동일한 정책 실험으로 취급하지 않는다.

## 2. 제안하는 1회 선택 계약

다음은 **직렬화 가능한 논리 스키마**다. 현재 Python `TypedDict`와 `Protocol`로 표현했고, `tool_args`의 필드는 도구별 스키마를 따른다. 결정형 정책의 모델 응답 형식은 연결 단계에서 확정한다.

```text
ActionPolicy.select(context: ActionContext) -> ActionDecision

ActionContext:
  decision_id: str                 # 실행·agent·task·단계의 안정적인 식별자
  agent_name: str
  task: {id: str, description: str, milestones: ...}
  observation: {environment: ..., agent_state: ..., other_agents: ...}
  history: [{tool: str, args: object, feedback: ...}]
  allowed_tools: [{name: str, description: str, args_schema: object}]
  budget: {remaining_steps: int, decision_timeout_s: number}

ActionDecision:
  kind: "invoke" | "finish" | "defer"
  tool_name: str | null            # invoke에서 필수
  tool_args: object | null         # invoke에서 필수; 실행 가능한 전체 인자
  message: str | null              # finish/defer의 설명; 성공 판정이 아님
```

- `allowed_tools`는 해당 agent에게 **실제로 제공된** `Agent.tools`와 실험에서 제한한 도구의 교집합이다. 도구 이름과 인자 스키마는 실행기에서 가져오며, 프롬프트에 적힌 행동 목록만 믿지 않는다. `recommended_actions` 같은 기존 별도 제한을 쓰면 양 정책에 동일하게 적용한다.
- `Task.id`는 코드에 있지만 `Task.to_json()`에는 빠져 있으므로, 입력 구성 시 식별자를 별도 필드로 전달해야 한다.
- `tool_args`에는 좌표·아이템·대상·수량·방향뿐 아니라 도구가 요구하는 `player_name`, `emotion`, `murmur` 등의 필드 책임을 정해야 한다. 불변 필드는 공통 실행기가 채울 수 있지만, 정책이 고르는 필드와 공통으로 채우는 필드는 실험 전에 고정한다. 동일한 인자 생성기를 두 정책에 제공할 수 없는 과제는 **도구 이름만의 진단 실험**으로 표시하고 전체 BA 정책 비교로 주장하지 않는다.
- `finish`는 정책이 더 이상 행동하지 않겠다는 제안이다. 작업 성공 판정은 기존 reflection과 환경 judger의 별도 결과를 따른다. `defer`는 선택 불가·지원 요청을 뜻하며 자동 성공으로 처리하지 않는다.
- `observation`은 양 정책에 같은 스냅샷을 준다. 원시 환경 상태를 한쪽에만 더 제공하거나, 한쪽에만 이전 실행의 은닉 대화 이력을 남기지 않는다. 필요한 대화·행동 이력은 명시적으로 `history`에 넣고 길이 제한을 기록한다.

## 3. 공통 검증·실행 결과

1. 정책 호출 전: task/agent 식별자, 허용 도구 집합, 도구별 필수 인자 스키마, 남은 단계·시간을 확정한다. 게임 상태로 확인 가능한 선행조건만 검증한다. 좌표의 실제 도달 가능성 등 알 수 없는 조건은 *사전 검증됨*으로 표시하지 않는다.
2. 정책 호출 후: `kind`와 필수 필드, `tool_name ∈ allowed_tools`, 인자 타입·범위·허용값 및 불변 필드를 검사한다. 무효 출력은 실행하지 않고 `invalid_choice` 또는 `invalid_args`로 기록한다. 예: `placeBlock`에는 item, x/y/z, facing이 필요하다.
3. 유효한 `invoke`만 기존 Minecraft 도구에 넘긴다. 도구 반환의 `status`·`message`와 예외를 그대로 관측에 넣는다. API의 성공 응답도 최종 구조물·요리 완성과 동일시하지 않는다.
4. 각 시도는 `selected → validation → execution → feedback`을 한 `decision_id`로 연결한다. 파싱 오류, 정책 타임아웃, 도구 실패, 환경 연결 실패, 최대 단계 종료, `finish`를 구분한다.
5. 무효 선택·타임아웃 때의 재시도 횟수와 생성형 정책으로의 fallback은 실험 조건으로 고정하고 **발생·추가 호출·지연·비용을 모두 기록**한다. fallback을 거친 실행을 결정형 단독 성공으로 세지 않는다. 연결 실패나 서버 장애는 모델 판단 오류와 분리한다.

## 4. 기존 기준선과 비교의 경계

첫 단계로 기존 API 생성형 `Agent.run()`의 실제 도구 호출·인자·피드백을 계약 스키마에 매핑했다. 오프라인 도구 fixture와 모의 `Agent.run()`으로 유효 호출, 무효 인자 차단과 기존 반환 형식을 확인했다. **Minecraft 포함 G/G 기준선의 동등성은 아직 검증되지 않았다.** 기존 ReAct 파서 오류나 중간 재시도를 삭제하거나 조용히 유효 행동으로 보정하지 않는다. 다음 단계에서 같은 계약을 사용하는 독립적 1회 선택 루프와 생성형 어댑터를 마련한다.

로컬 생성형 모델로 바꾸는 실행은 *모델과 배포 방식*의 변경이고, 결정 모델로 바꾸는 실행은 *모델과 선택 방식*이 함께 바뀔 수 있다. 두 결과를 정책 형태만의 인과 효과로 해석하지 않는다. TD·AC·SM 및 BA reflection의 모델/설정은 역할별로 명시하고 고정한다. 현 [`Controller.__init__()`](../../../pipeline/controller.py)은 AC와 BA의 reflection에 같은 모델 객체를 전달하고, Minecraft `Agent.run()`은 행동 선택용 모델을 자체 생성하므로 역할별 분리가 필요하다.

## 5. 최소 오프라인 통과 사례

실제 서버·외부 API 없이 같은 fixture를 G/D 어댑터 모두에 입력할 수 있어야 한다. 다음 사례의 기대 결과를 고정한다.

| 입력/선택 | 기대 |
| --- | --- |
| 허용 도구 `placeBlock`, 모든 필수 인자가 올바름 | 유효 `invoke`; 공통 실행기까지 전달 가능 |
| 허용 목록 밖 도구 선택 | `invalid_choice`; Minecraft 호출 없음 |
| `placeBlock`의 좌표·`facing` 누락/오류 | `invalid_args`; Minecraft 호출 없음 |
| `finish` 반환 | 실행 도구 없음; reflection/judger 성공을 자동 생성하지 않음 |
| 정책 타임아웃 또는 도구의 실패 응답 | 원인·재시도·fallback을 구분하여 기록 |

첫 과제의 실제 `allowed_tools`, 도구 인자 생성 주체, 관측 스냅샷의 최소 필드, 시간/단계 예산은 fixture를 만들 때 확정한다. 이후에만 코드를 연결하고 actor 포함 benchmark로 넘어간다.
