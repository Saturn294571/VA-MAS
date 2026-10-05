# Agent 수 증가에 따른 협업 효율 병목 조사 초안

> 상태: 임시 연구 초안  
> 범위: VillagerAgent의 Task Decomposer–Agent Controller 정책과 실행 경로에서 나타나는 확장성 병목 진단  
> 주의: 이 문서는 이기종 하드웨어 인지 할당 연구를 대체하지 않는다. 동일 조건의 agent 수 증가만을 먼저 분석하는 병렬 조사 축이다.

## 1. 출발점

VillagerAgent 논문의 *Agent Collaboration and Performance Dynamics*는 agent 수가 증가하면 성능이 일정 지점까지 향상된 뒤 감소한다고 보고한다. 논문은 자원 경쟁과 LLM의 관리 복잡성을 가능한 이유로 제시하지만, 원인별 분석이나 task별 최적 agent 수는 수행하지 않았다.

Table 6의 Construction 결과는 다음과 같다.

| Task | Agent 수 | Completion `C` (%) | VHR (%) | Efficiency `E` (%/min) | Balance `B` (%) |
|---|---:|---:|---:|---:|---:|
| Task0 | 1 | 100.00 | 100.00 | 12.96 | - |
| Task0 | 2 | 100.00 | 100.00 | 17.75 | 93.09 |
| Task0 | 4 | 100.00 | 100.00 | 17.41 | 81.64 |
| Task0 | 8 | 66.63 | 63.33 | 12.45 | 55.67 |
| Task64 | 1 | 35.25 | 36.25 | 1.92 | - |
| Task64 | 2 | 41.67 | 35.62 | 2.34 | 90.77 |
| Task64 | 4 | 46.67 | 39.38 | 3.28 | 88.91 |
| Task64 | 8 | 30.21 | 33.33 | 2.27 | 74.09 |

두 task 모두 8-agent 조건에서 완료율과 효율이 감소한다. 그러나 이 표만으로는 다음을 구별할 수 없다.

- task 자체에 8개 agent가 동시에 수행할 만큼 병렬 작업이 없었는가?
- Decomposer가 병렬화 가능한 task를 직렬적인 DAG로 만들었는가?
- Controller가 많은 task와 agent를 한 번에 판단하면서 배정 품질이나 응답 시간이 악화되었는가?
- Minecraft 공간·블록·상자 같은 공유 자원을 두고 actor들이 충돌했는가?
- LLM/API, State Manager 또는 Minecraft server가 공통 병목이 되었는가?
- 단순히 agent 수만 늘고 전체 workload는 고정되어 유휴 actor가 증가한 정상적인 수확체감인가?

따라서 현재 확인된 사실은 **해당 조건에서 중간 규모 이후 성능이 감소했다**는 것뿐이다. “최적 agent 수가 존재한다”거나 그 원인이 “LLM 관리 복잡성”이라는 설명은 별도의 검증이 필요하다.

## 2. 중심 연구 질문

> VillagerAgent에서 agent 수 증가에 따른 협업 효율 수확체감은 workload의 내재적 병렬성, Task Decomposer가 만든 계획의 병렬성, Agent Controller의 배정 정책·처리 비용, actor 실행 간섭 중 어디에서 발생하는가?

이 질문을 다음 네 개의 진단 질문으로 나눈다.

1. **Workload ceiling:** 원래 task가 제공하는 최대 병렬성은 얼마인가?
2. **Planning bottleneck:** Decomposer가 그 병렬성을 DAG에 얼마나 보존하는가?
3. **Allocation bottleneck:** ready task가 충분한데도 Controller가 actor를 놀리거나 부적절하게 배정하는가?
4. **Execution interference:** 올바르게 배정된 actor들도 공유 환경·서비스에서 서로 방해하는가?

여기서 목표는 당장 새로운 Decomposer나 Controller를 제안하는 것이 아니라, 먼저 수확체감이 생기는 위치와 조건을 식별하는 것이다.

## 3. 주 연구축과의 관계

| 구분 | 이기종 과제 할당 | Agent 효율 병목 조사 |
|---|---|---|
| 핵심 독립변수 | 장치별 연산·메모리 능력과 부하 | 동일 조건에서의 agent 수 |
| 중심 질문 | 어떤 actor가 어떤 task를 맡아야 하는가? | 몇 actor까지 유효하며 어디서 확장이 막히는가? |
| 우선 통제 | task, model, agent 수 | model, hardware, task, world 조건 |
| 주요 비교 | capability-aware 대 capability-blind | agent 수와 control-plane 조건별 scaling |
| 교차 가능성 | 적정 병렬도 안에서 이기종 actor를 배정 | 필요 이상 actor를 활성화하지 않는 admission 정책 |

두 축을 초기부터 한 실험에 섞으면 agent 수 효과와 장치 이질성 효과를 구분하기 어렵다. 병목 조사에서는 우선 동일 model·동일 hardware 조건을 사용한다. 이후에 확인된 유효 병렬도와 병목 지점은 이기종 scheduler가 몇 actor를 활성화하고 어디에 배정할지 결정하는 근거가 될 수 있다.

## 4. 분석 단위와 용어

### 4.1 실행 흐름

```text
고수준 task
    ↓
Task Decomposer / TaskManager
    ↓  subtask DAG와 candidate 제약
ready task 집합
    ↓
Agent Controller / GlobalController
    ↓  task–agent 배정
Base Agent 실행
    ↓
Minecraft·LLM·State Manager
    ↓
결과 반영과 재계획
```

### 4.2 시간을 분해하는 최소 정의

각 subtask `i`에 대해 다음 timestamp를 기록한다.

- `t_created`: DAG에 생성된 시각
- `t_ready`: 모든 predecessor가 완료되어 실행 가능해진 시각
- `t_dispatch_start`: Controller가 배정 판단을 시작한 시각
- `t_assigned`: 유효한 task–agent 배정이 확정된 시각
- `t_execution_start`: actor가 실제 실행을 시작한 시각
- `t_execution_end`: actor 실행이 끝난 시각
- `t_committed`: task 결과와 상태가 graph에 반영된 시각

이를 통해 다음 구간을 구분한다.

```text
dependency wait = t_ready - t_created
controller wait = t_dispatch_start - t_ready
allocation time = t_assigned - t_dispatch_start
launch wait = t_execution_start - t_assigned
actor execution = t_execution_end - t_execution_start
state commit = t_committed - t_execution_end
```

전체 완료 시간만 측정하면 어느 구간이 agent 수에 따라 증가했는지 알 수 없다.

## 5. 원인 가설과 식별 신호

### H1. Workload의 내재적 병렬성 한계

task의 선행관계 때문에 동시에 실행할 수 있는 작업 수가 적다면 agent를 추가해도 성능이 개선되지 않는다. 이는 정책 실패가 아니라 workload의 정상적인 scaling ceiling이다.

관측할 값:

- task DAG의 node 수와 edge 수
- DAG width 또는 시점별 ready-task 수
- critical-path 길이
- `ready task 수 / 가용 agent 수`
- dependency 때문에 idle인 actor 시간

지지 신호:

- agent가 idle이지만 ready task가 없음
- Controller 지연과 actor 충돌은 작음
- agent 수보다 DAG의 최대 ready-task 수가 작음

### H2. Decomposer가 병렬성을 충분히 표현하지 못함

환경상 독립적으로 실행할 수 있는 작업도 Decomposer가 불필요한 dependency를 만들거나 너무 큰 subtask 하나로 묶으면 병렬성이 사라진다. 반대로 지나치게 잘게 나누면 재계획·배정·상태 공유 비용이 실제 작업 시간보다 커질 수 있다.

관측할 값:

- 한 graph round에서 생성된 subtask 수
- subtask 평균 실행 시간과 크기 분포
- dependency edge 밀도
- 독립 실행 가능하지만 edge로 연결된 false dependency 후보
- graph 재생성 횟수와 Decomposer LLM latency/token
- 재계획 전후 node의 중복·취소·재생성 비율

지지 신호:

- 환경상 병렬화 가능한 gold/manual plan보다 생성 DAG의 width가 작음
- agent 수가 늘어도 생성 subtask 수나 ready width가 증가하지 않음
- 지나치게 작은 task가 증가하면서 control-plane 시간이 커짐

### H3. Decomposer의 candidate 지정이 Controller를 과도하게 제한함

공개 코드에서는 TaskManager가 subtask의 `assigned agents`를 만들어 candidate list와 필요 인원수로 변환한다. Controller는 이 제한 안에서만 free actor를 선택한다. 따라서 논문상 Decomposer와 Controller로 분리된 할당 책임이 실제 코드에서는 겹친다.

관측할 값:

- task별 candidate 수와 전체 agent 수의 비율
- ready task인데 candidate가 모두 busy여서 대기한 시간
- candidate 제약 때문에 유휴 actor가 있어도 할당되지 못한 횟수
- candidate 제약 완화 시 가능한 추가 matching 수

지지 신호:

- free actor와 ready task가 동시에 존재하지만 candidate 교집합이 없음
- candidate 제약을 제거한 deterministic matching에서는 idle 시간이 감소함

### H4. Controller의 판단 비용과 할당 품질 저하

Controller prompt에는 environment, experience, agent state, free-agent 목록과 task 목록이 포함된다. agent와 task가 늘면 입력 길이와 가능한 조합이 증가하여 LLM latency, token 사용량, invalid assignment 또는 불안정한 선택이 늘 수 있다.

관측할 값:

- Controller 호출별 agent 수, task 수, prompt/completion token
- LLM 응답 latency와 재시도 횟수
- 반환한 assignment 수와 validation 후 남은 assignment 수
- invalid task, busy agent, candidate 위반, 중복 agent 등 rejection 사유
- ready task가 배정되지 않은 이유
- 동일 상태를 반복 입력했을 때 assignment 일관성

지지 신호:

- actor 실행이 아니라 Controller allocation time이 agent 수에 따라 증가
- invalid/rejected assignment와 미배정 task가 증가
- deterministic controller로 교체했을 때 scaling 저하가 완화됨

### H5. 실행 계층의 공유 자원 경쟁과 간섭

여러 actor가 동시에 실행되면 동일 block, container, 경로, crafting resource를 놓고 충돌할 수 있다. LLM API 동시 호출 제한, Python thread pool, agent별 HTTP service, Minecraft server tick도 공통 병목이 될 수 있다.

관측할 값:

- 동일 대상·위치·경로에 대한 동시 action 수
- tool 실패, timeout, 재시도와 중복 작업
- API rate-limit과 LLM request queue time
- thread pool 대기 시간
- Minecraft tick 지연 또는 action 응답 latency
- State Manager update와 shared-state 대기 시간

지지 신호:

- ready task와 Controller 배정은 충분하지만 actor execution 시간이 증가
- actor 수 증가에 따라 충돌·timeout·재시도가 증가
- 별도 공간 또는 독립 자원을 준 조건에서는 감소 현상이 완화됨

### H6. 상태 최신성 저하와 재계획 증폭

동시 actor가 많아질수록 관측과 상태 반영 사이의 간격이 커지고, Controller가 오래된 상태에 근거해 배정할 가능성이 있다. 잘못된 배정이 실패·재시도·재계획을 늘리면 병목이 증폭된다.

관측할 값:

- observation 생성부터 Controller 입력까지의 age
- task 배정 시점과 실제 실행 시점 사이의 state version 차이
- 이미 소진·이동된 자원을 전제로 한 action 실패
- 실패 후 재계획 횟수와 반복 subtask 비율

지지 신호:

- agent 수와 함께 state age 및 stale-state 관련 실패가 증가
- 동일 작업을 중복 생성하거나 이미 완료된 작업을 다시 시도함

## 6. 최소 계측 설계

기존 정책을 바꾸기 전에 다음 event log를 추가하는 것이 우선이다.

```json
{
  "run_id": "...",
  "event": "task_ready | controller_call | assignment | execution | state_commit",
  "timestamp": 0.0,
  "graph_round": 0,
  "task_id": "...",
  "agent_id": "...",
  "ready_task_count": 0,
  "free_agent_count": 0,
  "candidate_count": 0,
  "prompt_tokens": 0,
  "completion_tokens": 0,
  "latency_ms": 0,
  "result": "...",
  "reason": "..."
}
```

최소 aggregate 지표는 다음과 같다.

| 계층 | 필수 지표 |
|---|---|
| 최종 결과 | completion, VHR, efficiency, makespan |
| scaling | speedup, parallel efficiency, marginal gain per added agent |
| Decomposer | DAG width, critical path, subtask granularity, graph regeneration 수·시간 |
| Controller | ready-to-assigned 시간, 호출 latency/token, invalid assignment, unassigned-ready task |
| Actor | busy·idle·blocked 비율과 idle/blocked reason |
| 간섭 | action collision, duplicate work, timeout, retry, API/server wait |
| 상태 | state age, commit latency, stale-state failure |

`parallel efficiency = speedup / agent 수`로 두되, VillagerAgent 논문의 `Efficiency E (%/min)`와 이름이 충돌하지 않도록 보고서에서는 둘을 분명히 구분한다.

## 7. 최소 실험 순서

### 단계 0. Table 6 재현 가능성 확인

- 공개 코드에서 Task0과 Task64의 정확한 설정을 식별한다.
- 동일 model, prompt, world seed, API budget 조건을 고정한다.
- 논문의 1·2·4·8-agent 구성을 실행할 수 있는지 확인한다.
- 완전한 수치 재현보다 감소 경향과 로그 수집 가능성을 먼저 확인한다.

### 단계 1. 기존 end-to-end scaling 측정

- agent 수: 가능한 범위에서 `1, 2, 4, 8`
- task: 우선 Construction의 쉬운 task와 복잡한 task 각 하나
- 반복: seed와 변동성을 보고할 수 있는 최소 반복 수를 예비실험으로 결정
- 변경하지 않는 것: Decomposer prompt, Controller prompt, model, hardware class

목적은 성능 곡선을 다시 그리는 것보다 agent 수 증가 시 시간이 어느 계층으로 이동하는지 확인하는 것이다.

### 단계 2. Decomposer와 Controller의 분리 실험

동일한 task plan을 고정하여 Decomposer 변동을 제거한 조건과, 매 run마다 원래 Decomposer를 호출하는 조건을 비교한다.

1. **Original:** 기존 Decomposer + 기존 LLM Controller
2. **Fixed DAG:** 사람이 검토한 동일 DAG + 기존 LLM Controller
3. **Fixed DAG + deterministic assignment:** 동일 DAG + 단순 규칙 Controller

해석:

- Original만 악화되면 Decomposer·재계획을 우선 의심한다.
- Fixed DAG에서도 LLM Controller만 악화되면 allocation 판단을 의심한다.
- deterministic 조건도 악화되면 workload ceiling 또는 실행 간섭 가능성이 커진다.

### 단계 3. 실행 간섭 통제

- 공유 자원·공간을 사용하는 원래 task
- 가능한 한 actor별 자원·공간을 분리한 task 변형
- LLM 호출을 직렬화한 조건과 허용된 동시 호출 조건

이 단계는 네트워크나 Minecraft 성능 자체를 새 연구 주제로 삼기 위한 것이 아니라, control-plane 병목과 execution-plane 간섭을 분리하기 위한 통제다.

## 8. 최적 agent 수를 정의하는 방법

모든 task에 통용되는 하나의 최적 agent 수를 찾는 것은 부적절하다. 최적점은 task의 병렬성, model, hardware, 비용 제약과 성공 기준에 따라 달라진다.

우선은 task `w`에 대해 다음 두 값을 보고한다.

- **성능 포화점:** agent를 추가했을 때 makespan 또는 completion 개선이 사전에 정한 최소 효과보다 작아지는 최초 지점
- **성능 붕괴점:** agent를 추가했을 때 completion 또는 efficiency가 통계적 변동 범위를 넘어 악화되는 최초 지점

비용까지 포함한다면 다음과 같은 효용 함수는 후보가 될 수 있다.

```text
utility(N, w)
= task success value
- α · completion time
- β · LLM/token cost
- γ · coordination overhead
```

하지만 `α, β, γ`를 임의로 정하면 결론이 달라지므로, 1차 보고에서는 원 지표와 Pareto trade-off를 먼저 제시하고 단일 utility는 연구자 판단 후 도입한다.

## 9. 결과 해석 규칙

- agent 수와 성능 저하의 상관만으로 Controller가 원인이라고 결론내리지 않는다.
- idle actor가 많아도 ready task가 없다면 할당 실패가 아니라 병렬성 한계일 수 있다.
- Balance 감소가 곧 성능 저하를 뜻하지 않는다. 일부 actor를 의도적으로 idle로 두는 것이 더 효율적일 수 있다.
- LLM token 증가와 latency 증가를 구분한다. token이 같아도 API queue나 rate limit 때문에 느려질 수 있다.
- 실패가 늘었다면 planning 오류, assignment 오류, action 충돌, state staleness를 별도 분류한다.
- Table 6의 Task0·Task64에서 관찰한 peak를 다른 task의 보편적 최적점으로 일반화하지 않는다.

## 10. 예상되는 연구적 연결점

병목 위치가 확인되면 다음과 같은 제한된 후속 기여를 검토할 수 있다.

- workload의 ready width에 따라 활성 actor 수를 조절하는 admission policy
- candidate 제약과 실제 free-agent 상태를 분리하는 할당 책임 정리
- LLM Controller 앞의 deterministic filtering·ranking
- critical path와 예상 실행 시간을 고려한 task–actor matching
- stale state 또는 충돌 위험이 큰 배정을 회피하는 정책

이 중 무엇을 실제 연구 기여로 선택할지는 계측 결과 이후 결정한다. 원인이 확인되기 전에 모든 정책을 동시에 구현하지 않는다.

## 11. 당장 확인할 코드 질문

1. TaskManager가 agent 수를 기준으로 subtask 수를 제한하는 정확한 위치와 방식은 무엇인가?
2. `required subtasks`, `candidate_list`, 필요한 agent 수가 graph와 Controller 입력으로 어떻게 변환되는가?
3. ready task와 free agent가 동시에 존재하지만 배정되지 않는 모든 분기 조건은 무엇인가?
4. Controller의 LLM 호출은 graph round마다 몇 번 발생하며 agent 수에 따라 prompt가 어떻게 커지는가?
5. thread pool의 worker 수와 실제 동시 실행 수는 agent 수를 따라가는가?
6. 여러 agent가 하나의 task에 배정될 때 역할 재분해 호출이 추가 병목을 만드는가?
7. task failure, timeout, reflection 결과가 graph 재생성과 중복 task에 어떤 영향을 주는가?
8. DataManager update가 동시 실행 결과를 어떤 순서와 일관성으로 반영하는가?

## 12. 임시 완료 기준

이 조사 초안의 다음 단계는 새 최적화 구현이 아니라 다음 증거를 확보하는 것이다.

- Table 6 또는 그 축소 조건의 실행 가능성
- agent 수별 end-to-end 결과와 단계별 timestamp
- 생성 DAG의 병렬성 및 actor idle reason
- Controller 호출 비용과 validation 탈락 사유
- actor 실행 간섭·재시도·상태 지연의 빈도

이 자료로 각 성능 저하 run을 `workload ceiling`, `Decomposer`, `Controller`, `execution interference`, `state feedback` 중 하나 이상으로 설명할 수 있다면 1차 진단을 완료한 것으로 본다.

## 근거

- VillagerAgent, §4.2 *Agent Collaboration and Performance Dynamics*: agent 추가에 따라 성능이 중간 수준까지 향상된 뒤 resource competition과 LLM management complexity 때문에 감소할 수 있다고 해석하지만 정확한 최적 범위는 제시하지 않는다.
- VillagerAgent, Appendix Table 6: Construction Task0·Task64의 1/2/4/8-agent 완료율, 효율, balance 결과.
- VillagerAgent, Figure 11 *Agent Controller Prompt Template*: 현재 상태, task 요구, 경험과 능력을 근거로 free agent를 task에 배정하도록 요구한다.
- [`villager_agent_architecture.md`](./villager_agent_architecture.md): 논문 모듈과 공개 코드의 대응, Decomposer–Controller 책임 중첩, 현재 Controller 경로의 제약과 검증 과제.
- [`os_network_idea.md`](./os_network_idea.md): scheduling, queueing, critical path, backpressure와 동기화 개념을 현재 연구 질문에 대응한 선행 메모.
