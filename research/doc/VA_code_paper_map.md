# VillagerAgent 아키텍처: 논문 개념과 공개 코드의 대응

## 문서 목적과 증거 범위

이 문서는 VillagerAgent를 **복잡한 공동 목표를 의존성 그래프로 나누고, 실행 가능한 하위 작업을 여러 Minecraft agent에게 배정한 뒤, 실행 결과를 다음 계획에 반영하는 중앙집중형 multi-agent orchestration framework**로 이해하기 위한 안내서다. 코드의 함수별 동작을 나열하기보다 논문이 제시한 기능 단위를 먼저 설명하고, 각 기능이 공개 코드의 어느 모듈에 구현됐는지를 연결한다.

근거는 다음 두 자료다.

- 논문: [VillagerAgent.pdf](../paper/VillagerAgent.pdf), 특히 §2, §3.1–3.5와 Appendix A.1·G
- 코드: `/home/pluto2479/Documents/MineSkynet-villager-agent`, 현재 `integration/villager-control-plane`의 commit `7edb5c6`

논문의 설계 설명은 **의도된 아키텍처**, 코드는 **현재 공개 구현에서 확인되는 동작**으로 구분한다. 아직 end-to-end 실행으로 검증하지 않은 코드 경로는 정적 분석 결과로만 다룬다.

## 1. 한눈에 보는 구조

VillagerAgent의 핵심은 agent들이 서로 자유롭게 대화하며 계획을 맞추는 구조가 아니라, 중앙 모듈들이 공동 상태와 task graph를 관리하고 Base Agent가 배정된 작업을 실행하는 구조다.

```text
고수준 목표·task data
        |
        v
Task Decomposer ── 현재 환경·agent 상태를 참고해 subtask DAG 생성
        |
        v
Agent Controller ── 선행 작업이 끝난 subtask를 가용 agent에게 배정
        |
        v
Base Agents ─────── ReAct로 Mineflayer tool을 선택·실행하고 자체 완료 판정
        |                                      |
        | action·observation·feedback          | Minecraft interaction
        v                                      v
State Manager <───────────────────────── VillagerBench / Minecraft
        |
        └── 갱신된 환경·agent 상태와 실행 결과를 다음 분해·배정에 제공
```

이 흐름은 한 번의 고정 계획으로 끝나지 않는다. 한 실행 round가 정리되면 성공·실패 기록과 새 환경 상태를 바탕으로 task graph를 다시 생성할 수 있다. 따라서 DAG는 전체 episode 동안 불변인 계획이라기보다 **현재 상태에서 실행할 작업들의 갱신 가능한 coordination plan**에 가깝다.

## 2. 논문–코드 기능 대응표

| 논문의 기능 단위 | 논문에서의 책임 | 공개 코드의 주 대응 | 대응 정도 |
|---|---|---|---|
| Task Decomposer (§3.2) | 목표를 subtask로 분해하고 선후·병렬 관계를 DAG로 표현하며 실행 결과에 따라 갱신 | [`TaskManager`](../../../MineSkynet-villager-agent/pipeline/task_manager.py), [`Task`·`Graph`](../../../MineSkynet-villager-agent/type_define/graph.py), [`task_prompt.py`](../../../MineSkynet-villager-agent/pipeline/task_prompt.py) | 대체로 직접 대응. 코드 이름은 Decomposer가 아니라 TaskManager |
| Agent Controller (§3.3) | 실행 가능한 node를 찾고 환경·agent 상태를 근거로 agent를 선택해 병렬 실행 | [`GlobalController`](../../../MineSkynet-villager-agent/pipeline/controller.py), [`controller_prompt.py`](../../../MineSkynet-villager-agent/pipeline/controller_prompt.py) | 기능상 대응하지만 분해기와 배정 책임이 일부 겹침 |
| State Manager (§3.4) | agent별 상태·행동 이력과 전역 환경 상태를 유지하고 task-relevant state를 제공 | [`DataManager`](../../../MineSkynet-villager-agent/pipeline/data_manager.py), [`data_prompt.py`](../../../MineSkynet-villager-agent/pipeline/data_prompt.py) | 직접 대응. 저장 상태의 최신성에는 구현상 제한이 있음 |
| Base Agent (§3.5) | 배정된 subtask를 ReAct로 실행하고 action history를 이용해 완료 여부를 self-reflect | [`BaseAgent`](../../../MineSkynet-villager-agent/pipeline/agent.py), [`agent_prompt.py`](../../../MineSkynet-villager-agent/pipeline/agent_prompt.py) | 직접 대응 |
| Minecraft action bridge | 논문의 Base Agent가 사용할 행동 API와 관측 제공 | [`Agent`](../../../MineSkynet-villager-agent/env/minecraft_client.py), [`minecraft_server.py`](../../../MineSkynet-villager-agent/env/minecraft_server.py) | 논문에서는 독립 core component가 아니라 Base Agent·환경의 실행 계층 |
| VillagerBench (§2) | construction, farm-to-table, escape room scenario와 자동 평가 제공 | [`VillagerBench`](../../../MineSkynet-villager-agent/env/env.py)와 `env/*_judger.py` | framework 외부의 benchmark·runtime 계층 |

논문의 이름과 코드 class 이름이 다른 핵심 대응은 다음과 같다.

```text
Task Decomposer  ≈ TaskManager
Agent Controller ≈ GlobalController
State Manager    ≈ DataManager
Base Agent       ≈ BaseAgent + Minecraft Agent bridge
```

## 3. Task Decomposer: 목표를 실행 가능한 DAG로 바꾸는 기능

### 논문의 설명

Task Decomposer는 고수준 목표를 작은 subtask node로 나누고, 먼저 끝나야 하는 작업 사이에 directed edge를 둔다. 직접 dependency가 없는 node는 병렬로 실행할 수 있다. 논문에서 각 node는 대략 다음 정보의 묶음이다.

```text
Nj = (Tj, Dj, Cj, Fj)

Tj: subtask 설명
Dj: 해당 subtask에 필요한 task data
Cj: 배정 후보 또는 배정된 agent
Fj: 실행 feedback
```

분해기는 전체 원본 data를 모든 agent에게 넘기지 않고 `retrieval paths`를 함께 생성해 node에 필요한 일부 data를 연결한다. 실행 결과가 누적되면 현재 환경, agent 상태, 이전 성공·실패를 참고해 다음 subtask 집합을 다시 만든다.

### 코드의 대응

`TaskManager`가 LLM으로 `description`, `milestones`, `retrieval paths`, `required subtasks`, agent 관련 필드를 생성한다. 이를 `Task` 객체로 변환하고 `Graph`가 node·edge와 실행 상태를 보관한다. 논문 Appendix A.1의 graph 변환과 마찬가지로 명시된 predecessor는 edge가 되고, predecessor가 생략된 후속 node는 앞 node의 predecessor 관계를 공유하도록 처리된다.

현재 기본 `update` 경로는 전체 장기 계획을 한 번에 만드는 대신 agent 수 이하의 가까운 subtask를 만들고, 한 round가 정리된 뒤 성공·실패 trace를 포함해 graph 전체를 다시 생성한다. 코드에 더 세밀한 graph 수정용 `merge` 경로도 있지만 생성자 인자와 별개로 기본 관리 방식이 `update`로 고정되어 있어, 기본 실행 경로로 간주하기 전 별도 검증이 필요하다.

### 기능적 의미

Task Decomposer는 단순한 자연어 task splitter가 아니다. VillagerAgent에서 coordination의 핵심 자료구조인 DAG를 만들고, **무엇이 병렬화 가능하고 무엇이 선행되어야 하는지**를 규정한다. 반면 실제로 어느 free agent가 지금 실행할지는 원칙적으로 Controller의 책임이다.

## 4. Agent Controller: ready task를 선택하고 agent에 배정하는 기능

### 논문의 설명

Agent Controller는 먼저 미실행 node 중 predecessor가 없거나 모든 predecessor가 성공한 node를 `Nready`로 선택한다. 그 다음 환경 상태 `E`, ready node, agent 집합과 agent 상태를 LLM에 제공해 `(agent, subtask)` 쌍을 생성하고, 서로 독립적인 배정을 동시에 실행한다.

따라서 논문상 할당은 다음 두 층으로 나뉜다.

1. **구조적 허용 여부:** dependency가 해소되어 지금 실행 가능한가?
2. **적합성 판단:** 가용 agent 중 누가 위치·보유 item·경험·능력 면에서 적합한가?

### 코드의 대응

`GlobalController`는 graph에서 열린 task를 받고, 미완료 predecessor가 없는 task만 available하게 만든다. busy agent를 제외하고 task가 요구한 인원수와 candidate list를 만족하는지 검사한 뒤, Controller LLM에 환경, agent 상태, task 목록과 free agent 목록을 제공한다. LLM의 JSON 배정은 다시 deterministic validation을 거쳐 존재하지 않는 task, busy agent, candidate가 아닌 agent를 제거한다.

승인된 배정은 thread pool을 통해 병렬 실행된다. 하나의 task가 여러 agent를 요구하면 Controller가 task 설명을 agent별 역할로 다시 세분화한 뒤 각각에 전달한다. timeout·예외·self-reflection 결과는 task 상태로 환류된다.

### 현재 할당 정책의 정확한 해석

공개 코드의 정책은 순수한 rule-based scheduler도, 완전한 LLM 자유 배정도 아니다.

```text
DAG dependency·busy 여부·candidate·필요 인원으로 실행 가능 집합 제한
                             ↓
     LLM이 현재 상태를 보고 task–agent 조합 제안
                             ↓
          코드가 제약 위반 배정을 다시 제거
```

즉 **제약 검사는 규칙 기반이고, 제한된 후보 안의 적합성 순위는 LLM 판단**이다. 논문과 prompt는 위치, inventory, 경험, 능력을 판단 근거로 제시하지만, CPU/GPU 성능, memory 용량, 추론 latency, queue 길이 같은 hardware·runtime 자원은 node나 agent state에 표현되지 않는다. 현재 MineSkynet이 추가하려는 지점은 이 후자의 allocation input과 policy다.

## 5. State Manager: 관측을 공유 가능한 상태로 바꾸는 기능

### 논문의 설명

State Manager는 두 종류의 상태를 유지한다.

- agent state `Si`: 행동, 보유 item과 주변 정보가 누적 요약된 장기 상태
- action history `Hi`: 최근 action·observation을 담는 단기 실행 이력

각 agent의 local observation을 합쳐 global environment state `I`를 만들고, 고수준 task와 관련된 정보만 LLM으로 요약해 `E`로 제공한다. 이 상태는 Decomposer의 재계획, Controller의 배정, Base Agent의 실행에 공통 근거가 된다.

### 코드의 대응

`DataManager`는 Mineflayer 측 status를 받아 세 형태로 정리한다.

- agent별 현재 위치·보유 item·inventory·주변 정보
- 전체 agent의 관측을 모은 environment data
- 기존 요약과 최신 행동을 합친 agent별 running summary

`query_env_with_task()`는 원시 environment data에서 현재 task에 관련된 entity, block, creature와 상호작용 대상을 LLM으로 요약한다. Base Agent가 subtask를 수행한 뒤에는 action 결과와 새 status를 다시 받아 agent·environment·history를 갱신한다.

### 해석상의 주의점

코드의 global state는 강한 일관성을 보장하는 world model이나 database transaction이 아니다. 예를 들어 발견한 block 정보는 누적되지만 사라진 block의 제거를 일반적으로 추적하지 않고, 일부 주변 entity 정보는 마지막 update로 교체된다. 따라서 논문의 “current environment state”를 코드 수준에서 **항상 최신인 완전한 세계 상태**로 해석하면 안 된다. 이는 추후 state staleness를 측정할 때 별도의 검증 대상이다.

## 6. Base Agent: 배정된 작업을 Minecraft 행동으로 실행하는 기능

### 논문의 설명

Base Agent는 현재 subtask, milestone, 관련 task data, 환경 상태, 자신의 상태와 action history를 prompt에 넣고 ReAct 방식으로 action과 observation을 반복한다. 실행이 끝나면 action history와 milestone을 다시 비교하여 task 완료 여부와 요약 feedback을 생성한다. 이 feedback이 DAG node의 상태 갱신과 다음 계획의 근거가 된다.

### 코드의 대응

`BaseAgent`는 Controller가 전달한 `Task`를 받아 실행 prompt를 만들고 `VillagerBench.step()`을 호출한다. 그 아래의 `Agent`는 LangChain의 structured-chat ReAct agent로 Mineflayer tool을 선택한다. 각 tool은 agent별 local HTTP service에 요청되고, service가 실제 Mineflayer bot으로 이동·채집·제작·배치·전달 등의 행동을 수행한다.

```text
BaseAgent의 자연어 subtask
        ↓
ReAct tool 선택
        ↓
Python tool wrapper
        ↓ HTTP
agent별 Flask service
        ↓
Mineflayer bot / Minecraft server
        ↓
관측·오류·행동 이력 반환
```

실행 후 `BaseAgent.reflect()`가 task description, milestone, agent summary와 action history를 LLM에 제공해 `task_status`를 판정한다. Controller는 이 결과로 node를 success 또는 failure로 바꾸고 TaskManager에 feedback을 전달한다. benchmark의 최종 score를 계산하는 scenario judger와 Base Agent의 self-reflection은 서로 다른 판정 계층이므로 구분해야 한다.

## 7. 한 episode의 실제 제어 흐름

1. `VillagerBench`가 agent별 Mineflayer service를 띄우고 초기 local observation을 수집한다.
2. `DataManager`가 local observation을 agent state와 global environment data로 정리한다.
3. `TaskManager`가 고수준 목표와 task-relevant environment를 받아 subtask DAG를 생성한다.
4. `GlobalController`가 dependency가 해소된 task와 free agent를 찾는다.
5. Controller LLM이 제한된 후보 안에서 task–agent 배정을 제안하고, 코드가 제약 위반을 제거한다.
6. 배정된 `BaseAgent`들이 ReAct를 통해 Mineflayer tool을 병렬 실행한다.
7. `DataManager`가 각 실행 뒤 agent·environment·history를 갱신한다.
8. Base Agent의 self-reflection이 subtask 성공 여부와 feedback을 생성한다.
9. Controller가 agent를 free 상태로 돌리고 task 결과를 `TaskManager`에 전달한다.
10. 아직 실행 가능한 기존 node가 있으면 다음 배정을 수행하고, 현재 graph round가 정리되면 최신 상태와 성공·실패 trace로 subtask graph를 다시 생성한다.
11. benchmark scenario에서는 별도 judger가 world state를 바탕으로 completion score를 기록한다.

이 구조에서 Controller는 “전체 목표를 직접 수행하는 agent”가 아니라 **task graph의 진행과 worker 배정을 조정하는 control plane**이며, Base Agent는 **자신에게 주어진 subtask를 실제 환경에서 수행하는 actor**다.

## 8. 논문 설명과 공개 코드가 정확히 일치하지 않는 지점

다음 항목은 사소한 구현 세부사항이 아니라 아키텍처와 실험 해석에 영향을 주므로, 실제 실행 전에 확인해야 한다.

### 8.1 Decomposer와 Controller의 할당 책임이 겹친다

논문은 Task Decomposer가 subtask DAG를 만들고 Agent Controller가 agent를 배정하는 것으로 설명한다. 그러나 코드의 기본 `update` prompt는 각 subtask에 `assigned agents`를 이미 생성하고, 이를 `candidate_list`와 필요 인원수로 바꾼다. 이후 Controller는 이 후보 제약 안에서만 agent를 선택할 수 있다.

따라서 현재 기본 구현에서는 실제 할당이 다음처럼 나뉜다.

- TaskManager: agent 후보와 요구 인원을 사실상 선결정
- GlobalController: 그 제약 안에서 현재 free agent와 task를 연결

MineSkynet에서 hardware-aware allocation을 평가하려면 후보 생성과 최종 배정 중 어느 책임을 변경하는지 먼저 고정해야 한다.

### 8.2 능력을 고려하라는 prompt와 실제 입력 사이에 공백이 있다

환경 계층은 agent별 등록 tool의 공통·고유 집합을 계산할 수 있고, Controller prompt도 “Agent's Abilities”를 고려하라고 지시한다. 하지만 현재 기본 분해·배정 호출에서는 이 tool description이 Controller 입력에 명시적으로 전달되지 않는다. `TaskManager.agent_describe`에도 값은 저장되지만 기본 분해 prompt에 연결되지 않는다.

즉 공개 코드만으로는 tool-level capability-aware assignment가 실제로 작동한다고 단정할 수 없다. hardware profile은 더더욱 현재 입력 schema에 없다.

### 8.3 experience 경로가 현재 코드에서 끊겨 있다

Controller는 배정 전에 `DataManager.query_task_list_experience()`를 호출하고, 이 함수는 각 task에 대해 `query_task_experience()`를 호출한다. 그러나 조사한 현재 `DataManager`에는 해당 method 정의가 없다. 논문 Figure 2와 Controller prompt에는 plan/action experience가 등장하지만, 현재 commit의 기본 배정 경로는 이 지점에서 실패할 가능성이 있다.

따라서 경험 기반 배정은 논문의 의도된 기능으로는 설명할 수 있으나, 현재 공개 코드에서 실행 검증된 기능으로 표기해서는 안 된다.

### 8.4 predecessor agent state 전달이 논문보다 넓다

논문은 현재 node의 predecessor에 참여한 agent 상태 `Sselected`를 실행 입력으로 설명한다. 코드는 Base Agent에게 다른 모든 agent의 running summary를 제공한다. 정보가 더 넓게 제공될 수는 있지만, 논문의 선택적 predecessor-state 전달과 정확히 같은 구현은 아니다.

### 8.5 실행·평가의 완료 판정이 이중화되어 있다

Base Agent의 self-reflection은 subtask 완료 여부를 LLM으로 판정하고 orchestration을 진행시킨다. 반면 VillagerBench의 scenario judger는 실제 Minecraft world state를 사용해 최종 score를 계산한다. 전자는 control feedback이고 후자는 benchmark measurement다. 두 결과가 불일치할 수 있으므로 실험에서는 각각을 따로 기록해야 한다.

## 9. MineSkynet 관점의 책임 경계

VillagerAgent를 MineSkynet의 주력 선행 구조로 사용할 때 보존해야 할 중심은 다음이다.

- TaskManager가 목표를 dependency-aware DAG로 표현하는 기능
- GlobalController가 ready task, free agent와 상태를 기준으로 배정을 관리하는 기능
- DataManager가 실행 관측을 공유 상태와 memory로 환류하는 기능
- Base Agent가 subtask를 action으로 실행하고 구조화된 결과를 반환하는 기능

MineSkynet의 연구 질문은 이 구조 전체를 교체하는 것이 아니라, Controller가 보는 agent profile에 **연산 능력, 가용 memory, 배치 가능한 model·context, 예상 latency와 현재 load**를 추가하고 그 정보를 고려한 배정이 기존 정책보다 유리한지를 검증하는 것이다.

```text
VillagerAgent baseline
  environment·inventory·경험·tool 능력 중심의 배정 의도

MineSkynet extension
  위 정보 + hardware/runtime capability와 load를 명시한 배정
```

Odyssey-derived actor service를 붙이더라도 고수준 분해, DAG 관리, 전역 상태와 최종 배정은 VillagerAgent control plane에 남긴다. Actor service는 배정받은 `subtask` 또는 `skill_id`를 실행하고 관측·오류·latency·resource 상태를 반환하는 경계로 제한하는 것이 현재 합의와 맞는다.

## 10. 현재 이해를 확인하기 위한 다음 검증

이 문서는 논문과 코드의 구조를 대응한 결과이며 실행 성공 보고가 아니다. 다음 재현 단계에서는 아키텍처 이해에 직접 영향을 주는 항목만 우선 확인한다.

1. 단일 bot이 Minecraft에 접속하고 등록 tool 하나를 실행하는지 확인한다.
2. `tiny_start.py`에서 TaskManager가 실제로 어떤 subtask·candidate를 생성하는지 기록한다.
3. 끊긴 experience 조회 경로가 Controller 진입을 막는지 확인한다.
4. Controller prompt에 실제로 전달되는 environment·agent state·candidate 정보를 보존한다.
5. Base Agent reflection과 benchmark judger의 판정을 별도 log로 비교한다.
6. 두 agent 이상에서 독립 DAG node가 실제로 병렬 실행되는지 확인한다.

이 검증이 끝난 뒤에야 “VillagerAgent의 기존 할당 정책”을 재현된 baseline으로 확정하고, hardware-aware scheduler와의 비교 조건을 설계할 수 있다.
