# VA 협업 효율 연구 마일스톤

최종 갱신: 2026-10-12

상태 표기: `[x]` 확인, `[~]` 일부 확인, `[ ]` 미완료

## 목표와 판단 원칙

> 에이전트 수 증가에 따른 VillagerAgent의 협업 효율 둔화·하락을, 작업 자체의 병렬성 한계와 TD 계획, AC 배정, actor 실행, 공통 서비스의 비용으로 나눠 설명할 수 있는가?

논문 Table 6의 Task0·64 결과는 현상의 출발점이지 원인의 증명이 아니다. 동일 workload에서 actor가 더 많아질수록 에이전트당 성과가 떨어지는 현상 자체를 실패로 부르지 않는다. 총 완료·시간·비용과 **왜 유휴 또는 지연이 생겼는지**를 함께 본다. 평가 기준과 예산은 본 비교 전에 고정한다.

## 1. 기존 VA 기준 경로 확인 `[x]`

논문 기능을 바꾸지 않고 실제 계획·배정·실행·점수 경로가 이어지는지 확인한다.

- [x] 원본 `controller.py`를 사용한 작은 Construction 실행을 확인했다.
- [x] Task20·3인에서 월드를 평지·Peaceful로 맞추고, actor 출력·파서·피드백 기록 문제를 다룬 뒤 한 실행이 12/12 블록·`complete task`로 끝났다.
- [x] 직접 배정과 LLM 배정을 로그상 구분하는 경로를 확인했다.

근거: [Task20 점수](../../../result/gemini-3.8-flash_construction_task20_3p_controller_llm_flat_20261007_trial2_feedback1024/score.json), [실행·진단 로그](../human_report/report_log.md). 이는 agent 수 변화의 인과 근거나 VA 원 논문 수치의 완전 재현이 아니다. 첫 실패 실행과 개선 뒤 성공 실행의 설정·코드 차이를 숨기지 않는다.

## 2. TD/AC만 분리해 과제 선택 `[~]`

actor 비용을 쓰기 전에 실제 그래프와 배정 선택지가 연구 질문을 드러내는지 확인한다.

- [x] [`td_ac_probe.py`](../../../td_ac_probe.py)로 Task25 첫 계획·배정을 검사했다. 합성 snapshot, 3 node·0 edge, 첫 라운드 9/15블록, 유효 배정 3개였다.
- [ ] Task50 또는 대체 Construction 과제에서 node·edge, 순환, ready 폭, 후보 제약, AC 직접/LLM 경로를 기록한다.
- [ ] 실제로 의미 있는 선행제약 또는 할당 선택지가 생기는 과제만 actor 포함 비교 후보로 올린다.

`Graph.add_edge()`가 순환을 보장하지 않으므로 DAG 분석 전 유효성을 검사한다. TD의 첫 라운드 부분 계획은 feedback 기반 재계획의 일부일 수 있다. **전체 과제를 한 번에 덮지 못함 = 계획 실패**로 판정하지 않는다. Task50의 선행 간선은 아직 관찰되지 않았다.

## 3. 병목 계측·재현 `[ ]`

agent 수가 달라질 때 성과 변화가 어느 단계에 해당하는지 식별한다.

- [ ] 실행마다 과제·world/seed·난이도·스폰·model·prompt·Controller 경로·코드 commit·agent 수를 고정/기록한다.
- [ ] 각 subtask의 `created/ready/assigned/start/end/commit`, ready task와 free actor 수, 후보 목록, 배정 제안과 수용/거절 이유를 수집한다.
- [ ] TD·AC·Base Agent·State Manager·judger의 호출 시간, token·비용, 재시도·종료 이유를 연결한다.
- [ ] world-state 최종 점수와 Base Agent reflection을 구분하고, 화면 기록은 로그 해석의 보조 증거로 사용한다.
- [ ] 선택한 agent 수와 조건에서 반복 실행 및 변동성을 보고한다. 반복 횟수·주 지표는 비교 전에 확정한다.

완료 기준은 적어도 하나의 지연·실패 패턴에 대해 **계획상 ready 부족 / 후보 제약 / AC 대기·오배정 / actor 간섭 / 공통 서비스** 중 어느 설명이 지지되고 어느 것은 아직 배제되지 않았는지 원시 로그로 제시하는 것이다. 미재현도 정식 결과다.

## 4. 필요한 이론과 한 가지 개선안 `[ ]`

관찰된 패턴과 직접 연결되는 기존 해결책만 조사한다. 선행관계 작업이라면 DAG scheduling·자원 제약 배정, 공간·상자 경합이면 동기화, 공통 호출 대기라면 queue/service capacity를 검토한다. 단순 정지로 deadlock, 호출 증가만으로 congestion을 선언하지 않는다. [개념 메모](../idea_hypothesis/os_nw_DAG_note.md)는 문제를 좁히는 참고 자료다.

원인이 재현되면 **한 변경**의 적용 전후를 같은 과제·조건에서 비교한다. 성공률·부분 완료, makespan, actor 유휴/활동, 단계별 대기, 호출·비용과 실패 유형을 함께 보고한다. 개선이 없거나 비용이 이득을 상쇄하면 그 조건을 명시한다.

## 5. 확장 여부 결정 `[ ]`

작은 과제에서 원인과 계측이 안정적일 때에만 Task64 및 더 많은 agent로 범위를 넓힌다. 이기종 하드웨어 인지 배정, Odyssey actor 이식, lifelong memory, 새 benchmark 구축은 별도 연구 질문과 독립 비교가 정해질 때까지 보류한다.

각 결과는 재현 명령, 코드 commit, model·API 설정, world/seed, 과제·agent 수, score, 로그 경로와 비용을 묶어 보존한다. component probe의 성공을 end-to-end 성공으로 올려 쓰지 않는다.
