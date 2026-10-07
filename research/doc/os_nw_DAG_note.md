# VillagerAgent 계획·할당 문제를 위한 OS·시스템 개념 메모

## 1. 연구 질문과 이 문서의 범위

현재의 중심 질문은 다음과 같다.

> 상이한 연산 능력과 메모리 제약을 가진 물리 장치들에 배치된 에이전트에게, 컨트롤러가 복합 작업을 적절히 할당할 수 있는가? 그리고 이러한 이기종 인지 할당은 동일 능력 에이전트들 또는 이기종성을 무시한 할당과 어떤 차이를 만드는가?

여기서 장치 성능과 메모리는 독립적인 연구 대상이라기보다 에이전트의 실행 시간, 수용 가능한 모델·문맥 크기, 동시 처리 능력을 제한하는 원인이다. 따라서 초기 실험에서는 모델의 지능 수준, context window, 에이전트별 지식까지 한꺼번에 바꾸기보다 **동일한 에이전트 기능을 서로 다른 자원 조건에서 실행했을 때의 작업 할당 문제**를 우선 다루는 편이 인과관계를 설명하기 쉽다.

이 문서는 수업 자료의 OS·컴퓨터 시스템 개념 가운데 이 질문과 직접 연결되는 것만 추린다. TCP 혼잡 제어 같은 일반 네트워크 문제 전체를 연구 범위에 넣지는 않는다. 이 프로젝트에서 우선 말하는 혼잡은 **작업 도착량이 처리 능력을 넘어서서 컨트롤러나 actor 앞의 큐가 누적되는 현상**이다.

## 2. VillagerAgent와 OS 개념의 대응

| VillagerAgent 구성요소 | OS·시스템 관점의 대응 | 관찰할 상태 |
|---|---|---|
| Task Decomposer가 만든 하위 작업과 의존 그래프 | job/process와 작업 DAG | 도착 시각, 선행 작업, 요구 자원, 예상 실행 시간 |
| Agent Controller | scheduler/dispatcher | 할당 결정, 우선순위, 큐 길이, 재할당 |
| actor와 그 actor가 배치된 장치 | processor/server | 연산·메모리 용량, 처리율, 현재 부하 |
| 할당 대기 중인 하위 작업 | ready queue | 대기 시간, 큐 길이, starvation |
| Minecraft·LLM 응답을 기다리는 actor | blocked process와의 유추 | 응답 대기 원인과 시간 |
| 선행 작업이 끝나기를 기다리는 하위 작업 | 아직 ready가 아닌 job | 선행관계 해제 시각과 dependency wait |
| State Manager와 작업 그래프 | 공유 상태·공유 자원 | 동시 갱신, lock 대기, 상태 일관성 |
| 작업 재할당 | migration/context switch | 상태·문맥 전달 비용, 이미 수행한 작업의 손실 |

이 대응은 VillagerAgent를 OS로 그대로 간주한다는 뜻이 아니다. 스케줄링 문제를 명확히 표현하고 비교군을 설계하기 위한 분석 틀이다.

### 2.1 작업 DAG와 ready queue는 서로 다른 층위다

Decomposer의 작업 DAG에서 노드는 하위 작업, 간선은 선행관계다. Controller가 실제로 배정할 수 있는 것은 그중 선행조건을 충족한 **ready task 집합**이다. 따라서 `목표 → 작업 DAG 생성 → ready task 선택 → agent 배정 → actor 실행·피드백`으로 나누어 보아야 한다. CPU ready queue를 선형 리스트로 표현하는 수업 요약은 실행 가능 작업을 보관하는 한 방식의 설명이지, 원래의 선행관계가 선형이라는 뜻이나 반드시 FIFO로 배정한다는 뜻이 아니다.

멀티프로세싱·멀티프로그래밍·멀티스레드는 여러 실행 단위가 어떻게 진행되는지 설명하지만, 자연어 목표를 어떤 크기의 하위 작업으로 **분할하고 다시 결과를 통합할지**는 별도의 계획 문제다. 스케줄링 개념은 DAG가 주어진 뒤의 대기·선택·실행 지연에 더 직접적으로 대응한다. 이 때문에 CPU 스케줄링만이 아니라 *선행관계가 있는 작업의 DAG scheduling*과 *자원 제약 작업 할당*을 후속 이론 후보로 본다.

현재 코드에서 `Graph.edge`는 선행 노드의 쌍이며 수치 가중치는 없다. Controller는 predecessor와 가용 candidate를 확인해 배정한다. 기존 단일-agent 검증에서는 생성된 작업 간선이 없어 DAG 의존성에 따른 병렬성 제한을 시험한 것으로 볼 수 없다. 향후 선행 간선이 실제로 있는 소규모 건설 과제에서 `created/ready/assigned/start/end`, agent 상태, 동일 좌표·자원 접근과 실패 feedback을 함께 기록해야 그래프 폭·critical path, 할당 지연, actor 실행 간섭을 분리할 수 있다.

## 3. 가장 직접적으로 가져올 개념

### 3.1 스케줄링 목표는 하나가 아니다

수업 자료는 CPU 사용률, 처리량, 대기 시간, 응답 시간, 반환 시간, 공평성, starvation 방지를 서로 다른 평가 기준으로 제시한다. VillagerAgent에서도 "좋은 할당"을 단일 지표로 정의하면 안 된다.

- **성공 여부**: Minecraft 작업을 실제로 완료했는가
- **makespan**: 한 복합 작업의 모든 하위 작업이 완료될 때까지 걸린 시간
- **대기·응답 시간**: 작업 생성부터 할당·실행 시작까지, 또는 완료까지 걸린 시간
- **처리량**: 단위 시간당 완료한 작업 수
- **장치 이용률**: 장치가 실제 추론·행동에 사용된 시간 비율
- **공평성·starvation**: 특정 actor나 긴 작업이 계속 배제되는가
- **스케줄링 오버헤드**: 성능 예측, 상태 수집, 재할당, 문맥 이전에 든 비용

연구의 1차 결과는 성공률과 makespan으로 두고, 처리량·대기 시간·이용률은 그 결과가 발생한 이유를 설명하는 보조 지표로 쓰는 구성이 적절하다.

### 3.2 FCFS와 convoy effect: 가장 단순한 비교군

FCFS는 도착 순서대로 작업을 처리하므로 구현이 쉽지만, 긴 작업 하나가 앞을 차지하면 짧은 작업들이 함께 지연되는 convoy effect가 생긴다. VillagerAgent에서는 다음과 같은 형태로 나타날 수 있다.

- 큰 추론 또는 긴 Minecraft 행동을 요구하는 하위 작업이 actor의 큐 앞을 막음
- 해당 actor가 느린 장치에 배치되어 후속 작업 전체가 늦어짐
- 선행 작업의 지연이 작업 DAG의 후속 작업으로 전파됨

따라서 `FCFS + 먼저 빈 actor`는 능력 비인지 비교군으로 유용하다. 다만 FCFS의 약점을 보이는 것 자체가 연구 기여가 되어서는 안 되고, 이기종 인지 정책과 비교하기 위한 하한선으로 사용해야 한다.

### 3.3 SJF/SRT: 작업 시간 예측과 actor별 실행 시간

SJF는 짧은 작업을 먼저 실행하여 평균 대기 시간을 낮출 수 있지만, 실제 실행 시간을 미리 알아야 하며 긴 작업의 starvation을 유발할 수 있다. 이 프로젝트에서는 작업의 실행 시간이 actor마다 달라진다는 점이 더 중요하다.

작업 `i`를 actor `j`가 수행할 때의 예상 실행 시간을 `p_ij`라고 두면, 단순히 "가장 짧은 작업"을 고르는 대신 **각 actor에서 언제 끝날지를 예측하는 할당**으로 확장할 수 있다. 메모리 요구량이 actor의 가용 메모리를 넘으면 그 조합은 애초에 실행 불가능한 것으로 처리한다.

이때 필요한 것은 거대한 성능 예측기가 아니라, 먼저 소규모 calibration을 통해 작업 유형별·장치별 실행 시간과 실패 여부를 기록하는 것이다. 예측 오차도 함께 보고해야 한다. 실행 시간을 완벽히 아는 oracle 정책은 실제 정책이 아니라 성능 상한 비교용으로만 둘 수 있다.

### 3.4 Priority, aging, HRN: 중요 작업과 starvation의 균형

작업 DAG의 critical path에 있는 작업, 다른 작업들이 결과를 기다리는 작업, 메모리 요구가 큰 작업에는 우선순위를 줄 이유가 있다. 그러나 강한 actor에 짧고 중요한 작업만 계속 보내면 긴 작업이나 약한 actor가 영구적으로 배제될 수 있다.

- **aging**: 대기 시간이 길어질수록 우선순위를 올린다.
- **HRN의 관점**: 예상 서비스 시간뿐 아니라 이미 기다린 시간을 함께 고려한다.
- **동적 우선순위**: 선행 작업 완료, 큐 적체, actor 상태 변화에 따라 우선순위를 갱신한다.

이 개념들은 최종 정책 후보라기보다, 처리량 최적화가 starvation을 만들지 확인하는 안전장치로 유용하다.

### 3.5 선점과 문맥 교환: 재할당은 무료가 아니다

선점형 스케줄링은 반응성을 높일 수 있지만 문맥 교환 비용을 만든다. LLM actor의 작업을 중간에 중단하고 다른 actor에 넘길 때는 일반 CPU 문맥 교환보다 훨씬 큰 비용이 생길 수 있다.

- 대화 기록, 관측 상태, skill, 부분 계획을 전달해야 함
- 이미 수행한 Minecraft 행동은 쉽게 되돌릴 수 없음
- 이전 actor와 새 actor의 상태 이해가 다를 수 있음
- 추가 LLM 호출과 token이 발생함

따라서 첫 실험은 **하위 작업 단위의 비선점 할당**을 기본으로 하고, 실패·timeout 때만 재할당하는 편이 해석하기 쉽다. 세밀한 선점은 이후 연구 문제로 남기는 것이 적절하다.

### 3.6 다단계·피드백 스케줄링: 정적 사양과 관측 성능의 결합

Multilevel Feedback Queue는 작업의 관측된 동작에 따라 우선순위를 바꾼다. 이 아이디어는 장치 사양만으로 할당하지 않고 실제 실행 결과를 반영하는 데 쓸 수 있다.

- 초기값: GPU/CPU 성능, 메모리, 실행 가능한 모델 등 정적 capability
- 실행 중 갱신값: 최근 latency, 실패율, 큐 길이, 가용 메모리
- 피드백: 예상보다 느리거나 메모리 부족이 반복되는 actor의 신규 할당을 줄임

다만 피드백 정책까지 처음부터 구현하면 변수가 많아진다. 정적 capability-aware 정책을 먼저 검증한 뒤, 예측 오차를 보정하는 후속 정책으로 두는 편이 좋다.

## 4. 병렬성, 의존성, 병목

### 4.1 actor 수 증가가 선형 성능 향상을 보장하지 않는다

병렬 처리 자료의 핵심은 명령 또는 단계 사이의 의존성과 pipeline stall이다. VillagerAgent도 Task Decomposer가 만든 그래프에 선행 관계가 있으면, actor가 남아도 준비된 작업이 없어 놀 수 있다. 한 느린 actor가 critical path의 작업을 맡으면 나머지 actor 수를 늘려도 전체 완료 시간이 크게 줄지 않는다.

따라서 다음을 구분해야 한다.

- actor가 부족해서 생긴 지연
- 의존성 때문에 병렬화할 수 없어 생긴 지연
- 잘못된 actor 할당으로 critical path가 느려진 지연
- Controller·State Manager 같은 직렬 구간 때문에 생긴 지연

이는 "actor 수가 증가할수록 협업이 저하되는가"를 해석할 때도 중요하다. actor 수와 함께 준비 작업 수, 동기화 비용, 통신량이 어떻게 변했는지 측정하지 않으면 원인을 할당 정책으로 돌릴 수 없다.

### 4.2 작업 DAG와 critical path

할당 정책은 actor의 평균 속도뿐 아니라 작업 그래프에서의 위치도 고려할 수 있다. 예를 들어 같은 예상 실행 시간이라도 다수 후속 작업이 기다리는 작업을 강한 actor에게 보내는 것이 makespan을 더 줄일 수 있다.

초기 정책 후보는 다음처럼 단순화할 수 있다.

`예상 종료 시각 = actor의 현재 backlog + p_ij + 전달·초기화 비용`

메모리 제약을 만족하는 actor 중 예상 종료 시각이 가장 이른 곳을 선택하고, 동률일 때 critical path 우선순위를 적용할 수 있다. 이는 설계 후보이며 현재 합의된 최종 알고리즘은 아니다.

## 5. 혼잡을 작업 큐 문제로 해석하기

### 5.1 도착률과 서비스율

작업 생성 속도를 `λ`, actor `j`의 유효 처리율을 `μ_j`라고 생각할 수 있다. 작업들이 동일하지 않으므로 단순한 단일 큐 공식으로 정확히 표현할 수는 없지만, 장기간 `λ`가 가용 처리 능력을 넘으면 backlog와 대기 시간이 계속 증가한다는 직관은 유효하다.

이 프로젝트에서 관측할 혼잡 신호는 다음과 같다.

- ready queue 길이와 가장 오래 기다린 작업의 대기 시간 증가
- 특정 actor의 queue만 증가하는 부하 불균형
- State Manager lock 또는 Controller 결정 대기
- API rate limit, LLM 응답 지연, Minecraft 행동 응답 지연
- 메모리 부족으로 인한 실패·재시도·모델 unload/reload

여기서 네트워크 latency는 혼잡 원인 중 하나일 수 있지만, 곧바로 TCP congestion control을 연구한다는 뜻은 아니다.

### 5.2 admission control과 backpressure

수업 자료의 고수준 스케줄링은 어떤 작업을 받아들일지 정하고, 중간 수준 스케줄링은 활성 작업 수를 줄여 과부하를 완충한다. 이를 VillagerAgent에 대응시키면 다음 후보가 나온다.

- Decomposer가 한 번에 생성·활성화하는 하위 작업 수를 제한
- actor별 queue에 상한을 두고 과부하 actor에 신규 작업을 보내지 않음
- 메모리 여유가 기준 이하인 actor는 일시적으로 비활성화
- 선행 작업이 끝나지 않은 작업은 ready queue에 넣지 않음

이러한 backpressure는 처음부터 필수 구현할 기능은 아니다. 단일 benchmark가 안정적으로 실행된 뒤, backlog를 의도적으로 만드는 stress test에서 필요성을 검증하는 편이 낫다.

### 5.3 load balancing과 capability-aware scheduling의 차이

큐 길이를 똑같이 맞추는 것만으로는 이기종 환경의 균형이 되지 않는다. 처리율이 다른 두 actor에게 같은 수의 작업을 주면 느린 actor의 대기 시간이 더 길어질 수 있다. 또한 작업별 연산·메모리 요구가 다르면 동일한 작업 수도 동일한 부하가 아니다.

따라서 부하는 최소한 다음 세 요소로 표현해야 한다.

- 현재 queue의 **예상 잔여 작업량**
- 새 작업을 해당 actor에서 처리할 **예상 실행 시간 `p_ij`**
- 메모리 등 **실행 가능성 제약**

## 6. 공유 상태, 동기화, 교착 상태

### 6.1 task claim과 상태 갱신의 원자성

여러 actor가 동일 task를 가져가거나, 완료 상태와 Minecraft 관측 상태가 엇갈리면 중복 행동과 잘못된 후속 할당이 발생할 수 있다. 따라서 Controller의 task claim, 실행 상태 전환, 완료 기록은 논리적으로 원자적이어야 한다.

프로세스 상태의 `ready-running-blocked` 구분도 유용하다. 단순히 actor를 idle/busy로만 기록하면 LLM 응답 대기, Minecraft 응답 대기, 선행 작업 대기를 모두 실행 시간으로 오해할 수 있다.

### 6.2 producer-consumer와 bounded queue

Task Decomposer는 작업 생산자, actor들은 소비자로 볼 수 있다. 무제한 queue는 폭주 시 메모리와 대기 시간을 키운다. bounded queue는 과부하를 명시적으로 드러내고 backpressure를 적용하기 쉽게 한다. 다만 queue 자체를 바꾸기 전에 현재 Controller의 작업 생성·할당 경로와 State Manager의 상태 전이를 계측하는 것이 먼저다.

### 6.3 deadlock과 resource allocation

복합 Minecraft 작업에서 actor가 여러 자원이나 다른 actor의 결과를 서로 기다리면 교착 상태와 유사한 상황이 생길 수 있다. 수업 자료의 네 조건인 상호 배제, 비선점, 점유와 대기, 원형 대기는 진단 체크리스트로 쓸 수 있다.

여기서 **작업 DAG의 선행 간선과 실행 중 자원 대기 간선은 다르다.** 작업 DAG가 비순환이어도 공유 자원에 대한 대기가 순환할 가능성은 별개다. 반대로 작업 정지, 선행 작업 실패, 동일 좌표에서의 블록 배치 간섭만으로 deadlock이나 race condition을 판정할 수 없다. 현재의 Minecraft 공간 간섭은 가능한 설명이지 확인된 동기화 오류는 아니다.

- actor A가 자원 X를 점유한 채 B의 결과를 기다림
- actor B는 자원 Y를 점유한 채 A의 결과를 기다림
- Controller가 순환 의존성을 발견하지 못해 진행이 멈춤

대응 후보는 task/resource 그래프에서 순환을 검사하고, timeout 시 체크포인트에서 재할당하거나 일부 task를 취소하는 것이다. 단, 느린 추론을 deadlock으로 잘못 판정하지 않도록 정상 latency 분포를 먼저 측정해야 한다.

### 6.4 priority inversion

critical-path 작업이 높은 우선순위를 가져도, 그 작업이 필요한 공유 자원을 낮은 우선순위 작업이 점유하면 실제 진행은 막힌다. priority inheritance는 이러한 상황을 설명하는 참고 개념이다. 첫 구현에 그대로 넣기보다는 lock/resource 대기 시간을 기록하여 실제로 문제가 나타나는지 확인한다.

## 7. 캐시와 지역성: 보조 변수로 통제할 항목

캐시 자료의 locality, hit/miss, replacement 개념은 skill retrieval과 actor context 재사용을 이해하는 데 도움을 준다. 같은 종류의 작업을 최근 수행한 actor는 필요한 skill·상태가 이미 준비되어 더 빨리 실행할 수 있고, 모델 load/unload나 긴 문맥 재구성이 있으면 cold-start 비용이 커질 수 있다.

그러나 이것을 첫 연구 질문의 중심으로 삼으면 hardware-aware scheduling과 lifelong context가 다시 섞인다. 초기 실험에서는 다음 중 하나를 택해 통제하는 것이 좋다.

- 모든 actor를 동일한 cold/warm 조건에서 시작
- cache hit/miss와 모델 load 시간을 별도 기록
- 스케줄링 시간과 실제 추론·행동 시간을 분리 기록

지역성을 이용한 skill-aware placement는 이후 확장 후보로 둔다.

## 8. 초기 비교 정책과 실험에 주는 함의

### 비교 정책 후보

1. **Round-robin**: 장치 능력과 현재 부하를 보지 않음
2. **FCFS + first available actor**: 현재 VillagerAgent 동작과 가까운 단순 기준선으로 확인 필요
3. **Load-aware**: 가장 짧은 예상 backlog를 가진 actor 선택
4. **Capability-aware**: 메모리 제약을 검사하고 `p_ij`가 작은 actor 선택
5. **Capability + load-aware**: 현재 backlog와 `p_ij`, 전달 비용을 함께 고려
6. **Oracle**: 실제 측정된 실행 시간을 미리 아는 것으로 가정한 성능 상한; 실제 배포 정책은 아님

먼저 논문과 코드에서 기존 VillagerAgent Controller가 실제로 어떤 정책을 쓰는지 확인한 뒤, 중복되는 기준선은 정리해야 한다.

### 초기 실험 원칙

- 모델, prompt, task semantics는 가능한 한 고정하고 장치 자원 조건을 우선 변화시킨다.
- actor별·작업 유형별 latency, memory peak, 성공 여부를 먼저 calibration한다.
- 동일 능력 actor 구성, 이기종이지만 능력 비인지 할당, 이기종 인지 할당을 비교한다.
- 단일 task 안정화 후 복수 task/DAG, 그다음 backlog stress 순으로 확장한다.
- actor 수를 늘릴 때 작업 수와 의존성도 함께 보고한다.
- hardware tier와 model tier를 동시에 바꿀 경우, 결과를 하드웨어의 인과 효과라고 단정하지 않는다.

## 9. 작업 가설과 다음 확인 사항

다음은 확정된 주장보다 코드·소규모 실행으로 검증할 작업 가설이다.

- **H1**: 이기종 환경에서 capability-aware 정책은 round-robin 또는 능력 비인지 정책보다 실패율과 makespan을 낮춘다.
- **H2**: 그 이득은 장치 간 성능·메모리 차이, backlog, critical-path 작업의 비중이 커질수록 커진다.
- **H3**: 지나친 재할당은 문맥 이전과 재시도 비용 때문에 성능을 악화시킨다.
- **H4**: 단순 queue-length balancing보다 actor별 예상 잔여 실행 시간을 쓰는 정책이 이기종 환경에 적합하다.

코드 조사에서 우선 확인할 항목은 다음과 같다.

1. Controller가 작업을 어떤 자료구조에 보관하고 어떤 순서로 꺼내는가
2. actor 선택 시 capability, 현재 상태, 과거 실행 성능을 보는가
3. task dependency와 critical path를 표현하는가
4. task claim과 완료 상태가 원자적으로 갱신되는가
5. timeout, 실패, 재시도, 재할당 규칙은 무엇인가
6. task/actor별 latency·token·memory·queue time을 분리해 기록할 수 있는가

## 10. 지금은 범위에서 제외할 개념

- TCP congestion window, AIMD 등 패킷 계층 혼잡 제어의 직접 적용
- 자연어 소통 방식과 구조화 프로토콜의 비교를 동시에 연구하는 것
- 게임 내 지식·성격·역할 이질성과 장치 이질성을 한 실험에서 함께 바꾸는 것
- OS 수준의 실제 CPU preemption이나 process scheduler를 새로 구현하는 것
- cache/skill retrieval 최적화를 1차 기여로 삼는 것

이들은 무관해서가 아니라, 현재의 핵심 질문인 **물리 자원 제약을 고려한 복합 작업 할당**의 인과성을 흐릴 수 있어 후속 후보로 둔다.

## 11. 수업 자료 근거

페이지는 PDF 페이지 기준이다.

| 자료 | 참고 개념 | 이 문서에서의 사용 |
|---|---|---|
| [`컴시기말.pdf`](./컴시기말.pdf), pp. 1, 3–7 | 실행 단위, ready queue, 스케줄링, 동기화, 교착상태의 요약 | DAG와 ready 집합의 구분을 검토하는 출발점; 분해·할당 알고리즘의 직접 근거는 아님 |
| `2_학습자료/CS_06_Scheduling_handout.pdf`, pp. 1–6 | 고·중·저수준 스케줄링, 과부하 완충, scheduling 목표와 평가 지표, CPU/I/O-bound, 선점·비선점, FCFS/convoy effect, SJF·starvation·aging, HRN, Round Robin, SRT, priority, multilevel feedback queue | 할당 목표, 비교 정책, overload/backpressure, 재할당 비용 |
| `2_학습자료/CS_05_Process_handout.pdf`, pp. 5–6 | process state, ready/blocked, context switching | actor 상태와 대기 원인 분리 |
| `2_학습자료/중간/CS_03_Parallelism.pdf`, pp. 1–9 | pipeline, dependency, stall, throughput와 speedup | 작업 DAG, critical path, actor 증가의 비선형 효과 |
| `2_학습자료/CS_07_Synchronization_handout.pdf`, pp. 3, 7–10 | race condition, semaphore/monitor, producer-consumer, priority inversion | 공유 상태 일관성, bounded queue, resource 대기 |
| `2_학습자료/CS_08_Deadlock_handout.pdf`, pp. 1–6 | 교착 상태의 네 조건, prevention/avoidance/detection/recovery, safe state, timeout, checkpoint/rollback | 순환 의존·자원 대기 진단과 복구 |
| `2_학습자료/중간/CS_04_Cache_handout.pdf`, pp. 3, 8–11, 16 | locality, cache hit/miss, replacement, memory traffic | skill/context/model warm state를 보조 변수로 통제 |

`CS-performance.pdf`는 슬라이드가 이미지 기반이라 현재 텍스트 추출로 내용을 신뢰성 있게 인용하지 않았다. 성능 지표는 Scheduling 자료에 명시된 항목을 중심으로 정리했다.
