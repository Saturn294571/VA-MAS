# AC 작업 배정 계약

목적은 VA의 작업 분해·DAG·actor를 유지하면서 같은 ready 작업과 같은 agent 상태 아래 생성형·결정형 배정 정책을 비교하는 것이다. 이 문서는 기존 Controller의 직접 배정과 LLM 배정을 공통 형식으로 연결하기 위한 계약이며, 결정형 모델의 성능이나 Minecraft 전체 실행을 검증한 결과가 아니다.

## 기존 코드와 경계

[`TaskManager`](../../../../pipeline/task_manager.py)는 작업과 후보를 생성하고 [`Graph`](../../../../type_define/graph.py)에 선행관계를 저장한다. [`GlobalController`](../../../../pipeline/controller.py)는 선행관계와 유휴 agent를 확인해 후보 수가 필요 인원과 같으면 직접 배정하고, 나머지 선택지에 LLM 제안을 받을 수 있다. 과거 Tiny Controller의 직접 배정 구현은 `archive/full-features-20261104` 브랜치에 보존한다. 핵심에는 Full만 남긴다. 배정된 작업의 실행·reflection·환경 judger는 별도의 책임이다.

기존 LLM 응답의 `task_id`는 Controller `task_list`의 **0-based 인덱스**이며, `Task.id`는 실행 중 UUID다. 정책 계약은 UUID를 사용하고 기존 LLM 입출력과 맞닿는 어댑터만 인덱스를 UUID로 변환한다. `Task.to_json()`에는 UUID가 없으므로 별도 기록한다. TD가 후보를 미리 제한한 경우 AC의 후보 범위를 임의로 넓히지 않는다.

## 공통 선택 계약

```text
AssignmentPolicy.select(context: AssignmentContext) -> AssignmentDecision

AssignmentContext:
  decision_id: str
  graph_valid: bool; graph_error: str | null
  tasks: [{task_id: str, legacy_index: int, status: str, available: bool,
           predecessor_ids: [str], predecessors_successful: bool,
           candidate_ids: [str], required_agents: int}]
  agents: [{agent_id: str, free: bool}]
  observation: {environment: ..., agent_state: ..., experience: ...}

AssignmentDecision:
  kind: "assign" | "defer"
  assignments: [{task_id: str, agent_ids: [str]}]
  source: "direct" | "llm" | 정책 이름
```

`assign`은 한 번의 배정 batch를 제안하고, `defer`는 배정을 보류한다. 정책은 실행·성공을 보장하지 않는다. 배정 검증 결과는 수락된 항목과 거부 사유를 따로 반환하고 무효 응답을 유효 배정으로 고치지 않는다. 빈 응답·파싱 실패·timeout과 명시적 보류를 구분해 기록해야 한다. 구현된 기존 어댑터의 적용 범위와 미구현 항목은 아래에 적는다.

환경·agent 상태·경험은 정책 호출 시 관측한 동일한 스냅샷을 두 정책에 제공하는 목표다. 현재 기존 생성형 Controller는 해당 정보를 기존 프롬프트 경로에서 읽으므로, 전체 프롬프트를 동일한 구조화 관측으로 교체한 것은 아니다. 후보 구성·검증과 정책의 선택, 실행을 분리해 이후 생성형과 결정형이 동일한 계약으로 선택하도록 확장한다.

## 결정적 검증과 경합

1. 실제 graph의 정점·간선과 비순환성을 확인한다. graph가 없거나 잘못됐으면 배정을 거부한다. `Graph.add_edge()` 자체는 cycle을 검사하지 않는다.
2. 작업이 현재 목록에 있고 상태가 `unknown`이며 `available`인지를 확인한다. graph의 모든 선행 작업이 `success`여야 한다. 기존 `get_open_task_list()`가 실패 predecessor를 목록에서 제외할 수 있으므로 비어 있는 `predecessor_task_list`만으로 선행 성공을 추론하지 않는다.
3. 선택된 agent는 등록된 free agent이면서 TD 후보에 포함되어야 하며, 개수는 필요 인원과 정확히 같고 중복이 없어야 한다. 같은 batch에서 agent 또는 작업의 중복 예약을 거부한다.
4. 선택 당시 스냅샷의 유효성은 실행 시점의 유효성을 보장하지 않는다. 공통 validator를 실행 직전 현재 상태로 다시 적용한다. 기존 Controller의 스레드 간 공유 상태에는 전역 배정 lock이 없으므로 이 확인만으로 완전한 원자성을 보장한다고 주장하지 않는다.
5. tiny Controller는 현재 협업 작업을 실제로 첫 agent에게만 큐잉한다. 따라서 공통 계약 경로에서는 **필요 인원이 1인 작업만** 수락하고 다인 작업을 `unsupported_multi_agent`로 거부한다. full Controller의 기존 협업 분해·큐잉 경로는 유지한다.

## 기존 경로와 관측

기존 LLM 응답은 `LegacyAssignmentPolicy` 어댑터의 `select()`를 통해 계약으로 변환하고 공통 validator의 수락 항목을 기존 `task_instance`·`agent_instances` 형식으로 돌려준다. 직접 배정도 같은 validator를 통과한다. `direct`, `llm`과 거부 사유는 tracer에 구분해서 남긴다. 공통 `AssignmentPolicy`는 교체용 인터페이스이며, 현재 Controller LLM의 프롬프트·모델 호출 전체가 독립 구현체로 분리된 것은 아니다. 결정형 정책 및 자동 fallback은 구현하지 않았다.

이 검증은 이전 baseline의 permissive한 경우를 거부할 수 있다. 결과를 비교할 때 코드 버전과 거부 사례를 기록하고, 적용 전후 실행을 같은 조건의 반복으로 합치지 않는다. 무효 항목을 거부하면서 같은 batch의 독립적인 유효 항목은 허용한다.

## 오프라인 통과 사례

- 2개 ready 작업에 각각 다른 유휴 후보 배정은 수락한다.
- 실패·미완료 predecessor, cycle, graph 밖 간선, busy·비후보 agent, 인원 수 불일치, batch 내 중복 agent·task를 거부한다.
- LLM의 index와 UUID를 정확히 대응시키고 존재하지 않는 index와 잘못된 응답을 거부한다.
- 선택 후 agent가 바빠졌거나 predecessor 상태가 바뀌면 실행 직전 재검증에서 거부한다.
- tiny의 다인 작업은 거부한다. 서버·외부 API 없이 검사한 결과는 actor 포함 기준선 재현을 뜻하지 않는다.

검증 명령: `PYTHONPATH=. .venv/bin/python verification/assignment_contract_checks.py`. `td_ac_probe.py --self-test --output <새 경로>`로 기존 TD/AC 첫 라운드 연결도 오프라인에서 확인할 수 있다.
