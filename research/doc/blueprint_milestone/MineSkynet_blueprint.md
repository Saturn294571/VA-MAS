# MineSkynet 연구 청사진

최종 갱신: 2026-10-12

기준 시스템: VillagerAgent(VA)와 VillagerBench

문서 역할: 현재 연구 질문, 원인 가설, 실험의 판정 경계를 한곳에 둔다. 실행 순서는 [마일스톤](milestone_index.md), 날짜별 근거는 [리포트 로그](../human_report/report_log.md)를 따른다.

## 1. 연구 질문과 현재 범위

> VA에서 에이전트 수가 증가할 때 공동 작업의 효율과 에이전트당 효율이 둔화하거나 감소하는 원인은 무엇인가?

VA 논문의 Table 6은 Construction Task0·64에서 에이전트 수별 성과가 단조롭게 증가하지 않음을 보여 준다. 그러나 그 표만으로 작업 자체의 병렬성 한계, Task Decomposer(TD)의 부분 계획, Agent Controller(AC)의 배정, actor 간 간섭 또는 공통 서비스 병목을 구별할 수 없다. 현재 연구는 **기존 VA의 병목 위치를 측정·설명하는 것**부터 시작한다. 재현 가능한 원인이 정해진 뒤에만 한 가지 제한된 개선안을 같은 조건에서 비교한다.

이기종 컴퓨터의 연산·메모리 능력을 고려한 배정과 Odyssey actor/lifelong 이식은 과거의 구상이며, 이 단계의 독립변수나 필수 구현이 아니다. 해당 방향으로 돌아가려면 별도의 연구 질문과 비교 설계를 정해야 한다.

## 2. VA에서 관찰할 제어 흐름

```text
공동 목표·현재 월드 상태
  → TD/TaskManager: 부분 subtask 그래프·후보 agent 생성
  → ready task: 선행조건과 가용 후보를 만족하는 작업
  → AC/GlobalController: 직접 배정 또는 LLM 제안·제약 검증
  → Base Agent: Minecraft 행동, 실패·완료 reflection
  → State Manager·judger: 상태 갱신·재계획 / benchmark 점수
```

논문은 TD가 작업 의존관계를 만들고 AC가 배정한다고 설명한다. 공개 코드에서는 TD가 `assigned agents`를 통해 후보를 먼저 제한하므로 배정 책임이 둘 사이에 걸쳐 있다. AC가 언제 직접 배정하고 언제 LLM을 호출하는지도 로그에서 구분해야 한다. Base Agent의 자기평가는 후속 제어를 위한 피드백이고, benchmark judger의 월드 기반 점수는 최종 평가다. 이 둘이 어긋날 수 있으므로 따로 기록한다. 기능별 근거는 [VA 논문–코드 지도](../architecture_understand/VA_code_paper_map.md)를 본다.

그래프의 node는 subtask, edge는 선행관계다. 현재 edge에는 수치 가중치가 없으며, `Graph.add_edge()`는 순환을 검사하지 않는다. 위상 정렬·임계경로 같은 분석은 실제 그래프의 순환·유효성을 먼저 확인한 뒤 적용한다. 작업 DAG, 실행 중 자원 대기, 네트워크 혼잡은 서로 다른 현상이다.

## 3. 설명해야 할 경쟁 가설

| 가능한 원인 | 구별할 관측 신호 |
| --- | --- |
| 작업의 내재적 병렬성 한계 | 가용 agent보다 ready task가 적어, 정상 배정이어도 유휴가 남음 |
| TD의 계획 폭·후보 제약 | 독립적으로 수행 가능한 일이 계획에 없거나 후보 제한 때문에 free agent가 선택되지 못함 |
| AC의 관리 비용·배정 품질 | ready task와 적합한 free agent가 있는데도 배정 대기·LLM 호출·잘못된 제안이 증가함 |
| actor 간 자원·공간 간섭 | 배정과 시작은 정상인데 공유 상자·좌표·이동 경로에서 실행 대기·재시도가 증가함 |
| 공통 서비스·평가 계층 | LLM/API·서버·State Manager 지연, feedback 불일치 또는 종료 한도가 여러 actor에 함께 영향 |

10월 랩미팅의 큰 가설은 **에이전트 간 자원 경쟁**과 **LLM 기반 관리 복잡성 증가**이다. 표의 나머지 가능성은 이 두 가설을 성급히 확정하지 않기 위한 경쟁 설명이다. 특히 고정 workload에 agent만 추가했을 때 에이전트당 성과가 낮아지는 것은 그 자체로 정책 실패가 아니다. 어떤 단계의 대기·오류가 증가했는지를 같이 보여야 한다.

## 4. 검증 순서

1. **기준선 재현:** VA의 원본 `controller.py`, 명시된 모델·월드·과제 조건을 고정한다. Task0·Task6 검증과 Task20의 개선 후 12/12 완료는 실행 경로 확인이며, scaling 원인의 증거로 올리지 않는다.
2. **저비용 계획·배정 프로브:** [`td_ac_probe.py`](../../../td_ac_probe.py)로 actor 실행 없이 TD의 node·edge·후보·첫 라운드 coverage와 AC의 제안·수용 배정을 본다. Task25는 3 node·0 edge·첫 라운드 9/15블록, 유효 배정 3개였고 병목은 미관찰이다. Task50은 다음 후보이며 선행 간선 생성 여부조차 아직 미확인이다.
3. **병목이 드러나는 과제 선택:** 실제 선행 간선, 후보 제약 또는 공간 간섭의 가능성이 관찰된 작은 Construction case를 고른다. 부분 계획은 VA의 feedback 기반 설계일 수 있으므로 전체 그래프가 즉시 나오지 않았다는 이유만으로 실패 판정하지 않는다.
4. **actor 포함 반복 실행:** 같은 과제·월드·model·Controller 경로에서 에이전트 수를 바꾸되, 먼저 각 조건의 로그가 비교 가능한지 확인한다. 필요하면 Task64로 논문 Table 6과 연결하되, 난도·비용을 감안해 확대한다.
5. **원인별 대조:** 측정 결과가 특정 경로를 지지할 때에만 후보 제약, 배정 방식, 실행 간섭 완화 등 **한 요소**를 바꾼 대조 실행을 설계한다. 개선 부재도 결과로 남긴다.

## 5. 최소 계측과 판정

각 subtask에서 `created → ready → assigned → actor start → actor end → state commit` 시점을 남기고, TD/AC 호출·토큰·지연, 그래프 node/edge·순환 여부, ready task와 free actor 수, 후보 목록, 직접/LLM 배정 경로, 실패·재시도 이유를 연결한다. 전체 실행에는 benchmark completion·view hit·시간·API 비용, actor별 활동/유휴시간, 월드·seed·스폰·난이도·모델·commit을 붙인다. 기존 점수의 `efficiency`나 `balance`만으로 단계별 원인을 해석하지 않는다.

판정 예시는 다음과 같다. ready task가 없으면 우선 계획/작업 병렬성을, ready task와 free actor가 함께 있는데도 배정되지 않으면 후보·AC 경로를, 정상 배정 후 지연된다면 actor·공유 자원을 조사한다. 공통 API 또는 서버 지연이 함께 증가한다면 agent 간 공간 충돌로 곧장 귀속하지 않는다. 상관관계를 인과 주장으로 높이려면 관련 조건만 바꾼 반복 대조가 필요하다.

## 6. 결과물과 범위 경계

첫 산출물은 성능 개선 수치가 아니라 **병목을 단계별로 재현하고 다른 설명을 배제할 수 있는 trace와 간결한 분석**이다. 이후 개선안을 제안한다면 동일 benchmark·예산·측정 정의에서 전후를 비교한다. 새 benchmark, 전체 DAG 이론 정리, deadlock/congestion 단정, 물리 장치 라우팅과 Odyssey 통합은 현재 완료 조건에 넣지 않는다. 필요한 개념만 [OS·DAG 메모](../idea_hypothesis/os_nw_DAG_note.md)에서 검토한다.
