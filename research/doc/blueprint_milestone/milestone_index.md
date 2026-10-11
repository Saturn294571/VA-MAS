# MineSkynet 마일스톤 인덱스

최종 갱신: 2026-10-12

## 현재 목표

VillagerAgent(VA)에서 **에이전트 수 증가에 따른 협업 효율 저하**가 어디에서 생기는지 확인한다. 먼저 Task Decomposer(TD)의 계획 폭·후보 제약, Agent Controller(AC)의 배정·판단 비용, Base Agent의 실행 간섭, 공통 서비스 지연을 분리해 측정한다. 원인을 확인하기 전에는 새 할당 정책이나 Odyssey 이식을 연구의 필수 단계로 삼지 않는다. 질문과 판정 틀은 [연구 청사진](MineSkynet_blueprint.md)에 있다.

## 지금까지와 다음 결정

| 단계 | 상태 | 근거와 남은 판단 |
| --- | --- | --- |
| VA 원본 실행 경로 | 완료 | 원본 `controller.py`로 Task0·1인, Task6·3인 등 작은 Construction 경로 확인 |
| Task20·3인 환경/actor 안정화 | 해당 실행 완료 | 평지·Peaceful, 개선 후 12/12 블록·`complete task`; [점수](../../../result/gemini-3.8-flash_construction_task20_3p_controller_llm_flat_20261007_trial2_feedback1024/score.json). scaling 원인 판정은 아님 |
| Task25 TD/AC 분리 프로브 | 첫 라운드 완료 | [프로브](../../../result/td_ac_probe_task25_20261007/probe.json): 3 node·0 edge, 9/15블록 계획, 세 배정 유효. actor 실행·전체 완료는 검사하지 않음 |
| Task50 계획·배정 프로브 | 다음 과제 | 실제 간선·후보·ready 폭을 확인. 구조상 선행관계 가능성은 아직 가설 |
| 병목의 재현·귀속 | 미완료 | 선행/후보/실행 간섭이 드러나는 조건 선정, 시간·상태 로그 계측, 반복 비교 |
| 제한된 개선안 비교 | 보류 | 원인 근거가 확보된 뒤 한 요소만 변경 |

다음 결정점은 **Task50 또는 더 적절한 소규모 과제의 TD/AC 출력이 실제 선행제약·후보 병목을 제공하는가**이다. 없다면 미관찰로 보고하고 시나리오를 다시 고른다. 있다면 actor 포함 실행으로 넘어가 단계별 대기와 실패를 확인한다. Task64와 agent 수별 scaling은 그 뒤의 비교 후보이지 즉시 대규모 실행할 의무가 아니다.

## 문서 경계

- [연구 마일스톤](research_milestone.md): 단계별 완료 조건과 실험 기록 항목
- [재현·환경 작업의 범위](modernization_milestone.md): 현 VA 실행 기반과 보류한 Odyssey 현대화의 구분
- [VA 논문–코드 지도](../architecture_understand/VA_code_paper_map.md): TD·AC·State Manager·Base Agent 역할
- [랩미팅 초안](../human_report/labmeeting_temp.md): 다음 보고에서 선택·편집할 논점
- [리포트 로그](../human_report/report_log.md): 날짜별 실행·진단 경과와 원시 근거

과거 연구 방향은 Git 기록에 있으며 이 인덱스의 현재 완료 조건으로 유지하지 않는다.
