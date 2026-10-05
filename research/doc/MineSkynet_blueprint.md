# MineSkynet 연구 블루프린트

최종 갱신: 2026-09-09
문서 역할: MineSkynet이 무엇을 연구하고, 어떤 시스템과 비교 실험으로 가설을 검증하는지 설명한다.

설치 명령은 [`research/README.md`](../README.md), 현재 순서는 [`milestone_index.md`](./milestone_goal/milestone_index.md), Odyssey 구현 근거는 [`paper_code_dependency_map.md`](./paper_code_dependency_map.md)를 따른다.

## 1. 한 문장 정의

MineSkynet은 장치·모델 능력이 서로 다른 물리 edge agent들을 중앙 coordinator가 배정·감독하며, 작업 할당과 축적된 경험의 활용이 공동 목표 수행을 개선하는 조건을 탐구하는 연구 구상이다.

각 edge node는 공유 Minecraft 세계에서 독립된 avatar를 제어하는 agent로 구상한다. 노드 수와 장치·모델 조합은 실험설계 과정에서 정한다.

## 2. 연구 질문과 가설

### 연구 질문

> 장치와 모델의 능력이 서로 다른 Minecraft agent들을 중앙 cloud-tier coordinator가 배정·감독하면, 성공률·완료 시간·비용·에너지 측면에서 어떤 task와 조건에서 이점 또는 손해가 발생하는가?

위 연구 질문을 유지하며, 라우팅 관련 선행연구에서 세부 가설과 평가 방법을 검토한다. “Prerequisite가 있는 공동 과제를 반복 수행할 때 축적된 skill을 고려한 작업 할당이 현재 상태만 고려한 할당보다 성과를 개선하는가?”는 세부 질문 후보이며 기존 연구 질문을 대체하지 않는다. 연구 질문 자체의 변경은 연구자가 결정한다.

### 검토할 가설 후보

주 비교는 다중 에이전트 상황을 전제로, 동일한 물리 배치·agent 수·자원 조건에서 각 방법론을 비교한다. Minecraft agent 라우팅 관련 선행연구에서 적절한 비교 방법과 평가 기준을 찾고, 아래 후보 중 최종 가설을 선정한다.

1. agent별 성공률과 비용을 반영한 배정은 차이를 무시한 무작위·균등 배정보다 안정적이다.
2. **코드·스킬 개선:** 성공·실패 피드백으로 skill 내부 절차를 수정하면, skill을 고정한 조건보다 해당 task의 실행 안정성·효율이 개선될 수 있다. 다른 task로의 효과 전이는 별도로 검증한다.
3. **이력 기반 의사결정 개선:** skill 코드를 고정한 상태에서도 현재 관측과 누적 피드백을 함께 활용하면, 현재 관측만 사용하는 조건보다 skill 선택·순서·작업 할당이 개선될 수 있다.
4. 두 개선 축을 결합했을 때의 추가 효과를 검토한다. 통신·동기화·재시도와 이력 처리·skill 및 프롬프트 수정·검증 비용이 이득을 상쇄하는 조건도 함께 확인한다.

각 후보의 구체적인 개선 지표와 비교 방법은 미정이며 §7의 실험설계에서 구체화한다.

### 보조 비교 후보

서로 독립적인 subtask를 여러 agent가 병렬 수행할 때 단일 실행 agent보다 빨라지는지는 필요할 경우 별도 비교한다. 이는 다중 에이전트 내 방법론 비교를 보완하는 후보이며 필수 실험으로 확정하지 않는다. 수행한다면 planner의 물리적 분리를 유지하고 agent 수·연산 예산 차이를 명시한다.

목표는 MineSkynet이 항상 우월하다고 주장하는 것이 아니다. 이득이 생기는 조건과 실패하는 조건을 함께 설명하는 것이 연구 결과다.

## 3. 연구 기반: Odyssey를 어떻게 사용하는가

### 논문 개념

Odyssey는 자연어 목표를 계획하고, 기존 skill을 의미 검색해 선택·실행한 뒤 관측 결과로 성공 여부를 판단한다. MineSkynet은 이를 실행 기반으로 삼고, VillagerAgent의 다중 agent orchestration과 Voyager 계열의 지속적인 skill 축적·수정을 참고해 이기종 node 지원과 경험 기반 적응을 구상한다. 구체적인 결합 방법은 선행연구 조사와 설계 과정에서 정한다.

### 브랜치와 profile 역할

| 이름 | 연구에서의 역할 |
|---|---|
| `odyssey-legacy` / `master` | 논문·원본 코드·prompt·asset의 의미를 확인하는 source reference |
| `odyssey-modernized` | 동일한 논문 기능을 지원 가능한 dependency에서 실행하는 단일-agent baseline |
| `voyager-lifelong` | curriculum, code 생성·수정·검증과 능동 skill 축적을 보존하는 별도 baseline |
| `odyssey-full` | Odyssey에 Voyager식 능동 skill lifecycle을 결합한 확장 profile |
| `mineskynet-core` | modernized 기반에서 다중 agent 배정과 경험 기반 적응을 검증할 제안 시스템 |

modernization은 연구 기여가 아니라 안전한 실험 기반을 만드는 작업이다. legacy runtime과 속도를 경쟁시키지 않으며, 변경 후 논문 기능이 유지되는지를 현재 환경의 회귀로 확인한다.

### 보존하는 기능

- 40개 primitive와 183개 compositional skill
- 자연어 description과 Sentence Transformer 기반 semantic retrieval
- recursive prerequisite 실행
- MineMA actor의 candidate 선택
- planner–actor–critic, 실행 feedback과 재계획
- 논문의 task·prompt·성공 조건

Voyager의 능동 skill 생성·수정은 기본 Odyssey 재현과 섞지 않지만 삭제하지도 않는다. 별도 profile에서 재현해 MineSkynet scheduler 효과와 skill library 성장 효과를 분리한다.

## 4. 제안 시스템

### 한눈에 보는 구조

```text
공동 목표
   ↓
Global Orchestrator ── task 분해·agent 배정
   ↓                         ↑
Shared State Service ── 상태·inventory·진행 기록
   ↓                         ↑
Evaluator & Replanner ── 검증·재시도·재배정
   ↓
Edge Actor A / B / C ── 각자 skill 선택·Minecraft 실행
   ↓
공유 Minecraft world
```

### Global Orchestrator

논문 언어로는 장기 목표를 실행 가능한 subgoal로 바꾸는 planner에 해당한다. MineSkynet에서는 여기에 각 agent의 능력과 위치를 고려한 배정 기능을 추가한다.

- 공동 목표를 dependency가 있는 subtask로 분해한다.
- task별 예상 성공률, 시간, 이동·handoff 비용을 바탕으로 agent를 선택한다.
- 실행 중 상태가 바뀌면 남은 계획을 갱신한다.
- 배정 이유와 사용한 capability 값을 trace로 남긴다.

### Shared State Service

논문 언어로는 planner와 critic이 참고하는 environment state와 achievement history에 해당한다. 여러 agent가 서로 다른 상태를 보고하므로 하나의 권위 있는 기록으로 통합한다.

- agent 위치·inventory·현재 task와 heartbeat
- task dependency·담당 agent·진행 상태
- world observation과 item handoff
- model·skill·실행 결과의 revision과 timestamp

actor가 보고한 `SUCCESS`만으로 상태를 확정하지 않는다. inventory나 world-state 변화로 교차 검증한다.

### Evaluator & Replanner

논문 언어로는 critic, self-validation과 reflection에 해당한다. 실행 결과를 확인하고 같은 actor의 재시도, 다른 actor로의 재배정 또는 전체 재계획을 선택한다.

- 실행 오류와 task 실패를 구분한다.
- deterministic state check를 우선하고 필요한 경우에만 model critique를 사용한다.
- retry·reassign·replan의 이유와 비용을 기록한다.
- 반복 실패가 공유 상태를 오염시키지 않도록 task commit을 통제한다.

### Edge Actor Runtime

논문 언어로는 검색된 candidate 중 skill을 선택하고 Mineflayer로 실행하는 actor에 해당한다. edge actor는 허용된 skill 안에서만 행동하며 전역 계획을 임의로 바꾸지 않는다.

- 구조화된 atomic goal과 candidate skill을 받는다.
- 자신의 model 또는 rule로 정확한 skill ID를 선택한다.
- Mineflayer executor에 실행을 요청한다.
- observation, latency, resource usage와 오류를 반환한다.
- 확신이 낮거나 반복 실패하면 coordinator에 escalation한다.

## 5. 이기종 장치의 의미

현재 대상은 Raspberry Pi 4B 4GB, GTX 1050 Ti 장비와 RTX 3090 24GB 장비다. 정확한 역할은 미리 고정하지 않고 동일 atomic task의 측정 결과로 결정한다.

| 장치 유형 | 초기 예상 역할 | 연구에서 확인할 점 |
|---|---|---|
| Raspberry Pi | rule-based 또는 매우 제한된 actor | 약한 장치도 이동·운반 같은 task에 기여할 수 있는가 |
| GTX 1050 Ti | 소형·양자화 actor | 중간 난도 skill 선택과 비용 사이의 균형 |
| RTX 3090 | 강한 actor 또는 on-premise planner 후보 | 물리적 분리 전제에 맞춘 역할 배치와 planning·실행 비용 |

검색된 skill 중 하나를 고르는 bounded actor는 초기 실행 검증에 사용할 수 있다. 이는 lifelong 과정의 skill·프롬프트 수정을 제한하는 전제가 아니다. 중앙 planner의 전역 배정 역할을 유지하되, code repair를 담당할 node와 갱신 권한은 아직 확정하지 않는다.

Planner와 실행 node는 논리적 분리뿐 아니라 서로 다른 물리 호스트에 배치하는 것을 잠정 전제로 한다. Docker는 각 호스트의 환경 격리·배포 수단으로 검토한다. 한 호스트의 여러 컨테이너는 사전 기능검증에 활용할 수 있으나 물리적 분산 실험의 증거와 구분한다. 위 장치별 역할과 code repair 담당은 초기 구상이며, 실제 배치와 갱신 권한은 실험 조건에 맞춰 확정한다.

## 6. 공통 계약

### Task 계약

자연어 목표가 agent마다 다르게 해석되지 않도록 실행 task는 최소 다음 정보를 가진다.

```text
task_id, goal, dependencies, allowed_skills,
required/expected state, timeout, assigned_actor, revision
```

### 결과 계약

성공 메시지가 아니라 관측 증거로 task를 판정하기 위해 결과는 최소 다음 정보를 가진다.

```text
attempt_id, actor/model/skill revision,
before/after observation, status, failure_class,
latency, retry count, resource usage
```

### Capability 계약

scheduler가 막연한 “강한 장치/약한 장치”가 아니라 측정값으로 배정하도록 actor–task 조합별 성공률, 평균·P95 시간, memory/energy와 failure 유형을 기록한다.

## 7. 실험 설계

### 7.1. 선행연구에서 평가 기준 도출

MineSkynet의 개선을 비교 가능한 증거로 보여주기 위해 라우팅 연구 조사와 실험설계를 연결한다. VillagerAgent는 연구자가 선정하고 랩미팅에서 리뷰한 기준 논문이다. 다른 연구의 문제·방법·baseline·benchmark를 함께 비교해 기여 후보를 정한다.

기존 평가로 질문에 답할 수 있으면 이를 활용한다. 기존 연구가 답하지 못하는 독창적인 질문이 확인되고 기존 평가로 측정하기 어려울 때 새 실험 또는 benchmark를 설계한다. 새 benchmark 자체를 필수 산출물로 전제하지 않는다.

### 7.2. 배치 전제와 비교 변수

주 비교에서는 planner와 실행 node의 물리적 분리를 유지하고 할당·경험 활용 방식을 바꾼다. Planner와 실행 기능을 한쪽에 통합하는 Cloud-only와 Edge-only는 현재 설계의 기본 비교군에서 제외한다. 고정 역할, 무작위·균등 할당, 현재 상태·능력 기반 할당, 누적 피드백을 활용한 할당은 비교 후보이며 선행연구와 질문에 맞춰 선택한다.

단일-agent Odyssey는 기능 확인의 참조로 활용할 수 있다. 단일 실행 actor와 비교할 필요가 생기면 planner는 별도 물리 노드에 유지하고, agent 수·연산 예산 차이를 명시한 별도 비교로 설계한다.

### 7.3. 경험에 따른 개선의 두 축

성공·실패와 당시 조건을 축적하고 이를 이후 행동에 반영하는 lifelong in-context 구상을 다음 두 효과로 구분한다.

| 개선 축 | 갱신 대상 | 확인하려는 효과 |
|---|---|---|
| 코드·스킬 개선 | Skill 내부 절차·구현 | 같은 skill을 더 안정적·효율적으로 수행하는가? |
| 의사결정 개선 | Skill 선택·순서·작업 할당 | 현재 관측과 누적 피드백으로 더 나은 선택을 하는가? |

Skill retrieval은 경험 활용의 한 수단이다. 프롬프트 수정은 실행 코드 생성에 영향을 주는지, 선택·할당에 영향을 주는지에 따라 해당 축에 배치한다. 모델 가중치는 적응·평가 중 고정하는 구상이며, 현재 관측과 이력을 활용하는 것과 observation space 자체를 확장하는 것은 별도 변경으로 구분한다.

Filtering Learning Histories의 ICRL 논의는 경험 context에 따른 행동 적응의 개념 근거로 참조한다. 이 논문의 LHF는 사전학습 이력 선별 방법이므로 실행 중 기억·skill 갱신과 동일한 구현으로 취급하지 않는다. 외부 코드 수정에 따른 시스템 개선, 이력 기반 의사결정 개선과 장기적 유지·전이는 각각 검증할 대상이다.

두 축의 효과를 구분하는 다음 구성은 실험 후보이며 최종 protocol은 아니다.

| 조건 | 코드·스킬 갱신 | 실행 시 의사결정에 누적 피드백 제공 |
|---|---|---|
| 기준선 | 고정 | 없음 — 현재 관측 사용 |
| 스킬 개선 | 허용 | 없음 — 현재 관측 사용 |
| 의사결정 개선 | 고정 | 있음 |
| 결합 | 허용 | 있음 |

스킬 개선 조건에서도 수정 과정에는 피드백을 사용한다. 수정용 이력과 실행 의사결정에 제공하는 이력을 분리하고, 조건별 기억 저장소와 skill revision을 관리해 조건 사이에 학습 결과가 섞이지 않게 한다. 같은 초기 skill에서 출발해 수정 비용과 이력·추론 예산을 기록한다.

### 7.4. 과제·지표·통제 조건의 후보

고정 시간 내 목표 자원 확보, 재료 병렬 수집 후 공동 제작, 운반·handoff와 prerequisite가 있는 tech tree 진행을 최소 과제 후보로 검토한다. 여러 과제를 구현하기 전에 연구 질문을 드러내는지와 기존 benchmark의 활용 가능성을 확인한다. Atomic capability 측정도 선택한 할당 방법에 필요한 범위에서 수행한다.

- 주 지표 후보: 공동 목표 달성률, 목표 완료 시간, 고정 시간 내 목표 자원 확보량.
- 보조 지표 후보: 부분 달성, 중복 작업, retry·timeout·재할당, 추론 비용, 통신·동기화 비용, memory·energy.
- 통제 조건 후보: 물리 배치, agent 수, 장치·모델 조합, 초기 skill·prompt, 시작 자원, world 조건과 시간·추론·경험 예산.

변경하려는 요인 외에는 동일 조건을 적용한다. Executor·dependency의 공통 기준을 기록하되, skill 갱신 조건은 초기 revision과 이후 변경 이력을 구분한다. Coordination과 수정·검증 비용을 포함해 성과를 보고하며, 주 지표와 비용 처리 방식은 본실험 전에 정한다.

### 7.5. 목표에서 역산한 구현과 예비실험

가설 → 비교 방법 → 과제·지표 → 필요한 skill·관측 기능 순서로 최소 구현을 정한다. 실제 동작, agent 간 간섭, subgoal 이해와 측정 가능성은 예비실험·디버깅으로 확인한다. 각 수정에는 어떤 실험을 가능하게 하는지 연결한다.

예비실험에서 난이도와 측정 절차를 다듬은 뒤 본실험 조건을 고정한다. 개발에 사용하지 않은 seed·과제 변형, 반복 실행과 결과 변동성 보고를 계획한다. 피드백을 누적하는 평가에서는 무엇을 episode 사이에 유지·초기화하는지와 기억 공유 범위도 명시한다.

§2의 연구 질문과 이기종·다중 agent 구상을 유지하며, 세부 가설, 할당·피드백 단위, 기억·수정 정책, benchmark, baseline, 주 지표, 구체적인 노드 배치와 반복 규모를 검토한다. 연구 질문부터 필요한 구현까지 연결한 한 장의 설계 초안을 먼저 만들고 선행연구 비교와 연구자 판단으로 구체화한다.

## 8. 범위와 후속 연구

Visual pixel control, LHF 사전학습, internal MoE 변경과 대규모 full fine-tuning은 현재 우선 범위 밖에 둔다. Scheduler의 구체적 방법은 선행연구 조사 후 정한다. Skill 수정 허용과 검증되지 않은 JavaScript의 전역 배포는 구분하며, 수정안을 검증한 뒤 이후 수행에 반영하는 절차를 설계한다.

다중 agent orchestration과 lifelong in-context는 연구자가 필요하다고 명시한 구성 요소다. Lifelong 구상은 성공·실패 피드백 축적, skill·프롬프트 수정, 수정 결과 검증과 이후 활용을 포함한다. Registry 읽기 전용은 효과 분리를 위한 통제 조건으로 사용할 수 있으며, 전체 연구의 영구적인 제약으로 두지 않는다. 갱신 담당, 검증·배포·되돌림 방식과 장기 기억 범위는 최소 실험설계에서 결정한다.

## 9. 성공과 실패의 해석

선택한 가설에 대해 본실험 전에 비교 대상과 판정 기준을 명시한다. 다음은 판정 문장의 틀이며 확정된 성공 조건이 아니다.

> 동일한 배치·예산 조건에서 제안 요소가 선정한 baseline 대비 주 지표를 개선하는지 확인하고, 코드·스킬 갱신과 이력 기반 선택의 효과 및 추가 비용을 구분해 보고한다.

개선이 없거나 수정·재시도·조정 비용이 이득을 지우는 결과도 가설 검증 결과다. 어떤 조건에서 각 결과가 나타나는지와 변동성을 설명하고, 관측 후 유리한 지표로 성공 기준을 바꾸지 않는다.

## 10. 문서 경계

- 프로젝트 판단 원칙: [`PROMPT.md`](../PROMPT.md)
- 설치와 실행 명령: [`research/README.md`](../README.md)
- 현재 상태와 다음 순서: [`milestone_index.md`](./milestone_goal/milestone_index.md)
- Odyssey 재현 완료 조건: [`modernization_milestone.md`](./milestone_goal/modernization_milestone.md)
- MineSkynet 실험 단계: [`research_milestone.md`](./milestone_goal/research_milestone.md)
- 논문 기능과 구현 근거: [`paper_code_dependency_map.md`](./paper_code_dependency_map.md)
- 실행 계층 원시 증거: [`E0_test_evidence_2026-08-20.md`](./E0_test_evidence_2026-08-20.md)
