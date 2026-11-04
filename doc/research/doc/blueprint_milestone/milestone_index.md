# MineSkynet 마일스톤 인덱스

최종 갱신: 2026-10-24

## 현재 목표

VillagerAgent(VA)를 기준으로 **생성형 계획을 유지하면서 제한된 행동 선택(BA)과 작업 배정(AC)을 경량 결정 정책으로 분리했을 때의 성능–지연–비용 trade-off**를 검증한다. BA 행동 선택을 먼저 단일 축으로 비교하고, AC 배정은 실제 선택 기회와 비교 가능성이 확인된 뒤 진행한다. [연구 청사진](MineSkynet_blueprint.md)에 질문·2×2 조건·해석 경계가 있다.

이전의 *에이전트 수 증가에 따른 모든 효율 저하 원인 규명*은 현재 완료 조건이 아니다. S1-MAS·Jev-LiteMAS는 역할 분리의 선행 아이디어이며, 특정 JEV 모델의 채택이나 VA에서의 성능 이득은 아직 검증하지 않았다.

## 확인된 기반과 다음 결정

| 단계 | 상태 | 확인된 범위와 다음 판단 |
| --- | --- | --- |
| VA 기준 실행 경로 | 확인 | 원본 `controller.py`로 작은 Construction 경로를 실행했다. Task20·3인 개선 후 한 실행은 [12/12 블록과 완료 점수](../../../result/gemini-3.8-flash_construction_task20_3p_controller_llm_flat_20261007_trial2_feedback1024/score.json)를 남겼다. 새 정책 비교·원 논문 수치의 완전 재현은 아님 |
| TD/AC 첫 라운드 프로브 | 확인 | [Task25 프로브](../../../result/td_ac_probe_task25_20261007/probe.json)는 합성 snapshot·actor 0회 조건에서 3 node·0 edge·유효 배정 3개를 확인했다. 과제 완주·배정 병목 증거는 아님 |
| BA 행동 결정 경계·계측 | **다음 단계** | 현행 ReAct 도구 호출의 관측, 후보·인자, 선택, 실행, 피드백을 구별하고 공통 정책 계약이 가능한지 판단 |
| G/G 기준선 → G/D 단일 축 | 미시작 | 같은 과제·월드·TD/AC/SM·도구 제약으로 생성형/결정형 행동 정책의 효과 비교 |
| AC 배정 기회 → D/G 단일 축 | 보류 | 직접 배정과 LLM 배정의 빈도·의미 있는 대안부터 확인. 현재 Controller 주도 배정 경로는 Construction·동질 agent로 제한됨 |
| D/D 결합과 benchmark 확장 | 보류 | 단일 축의 안정된 결과가 나온 뒤 결합, 다른 과제와 인원 수의 일반화 검토 |

**다음 결정점:** BA/Minecraft Agent의 다음 행동을 *같은 관측과 같은 유효 행동·인자 집합* 아래에서 두 정책이 선택하게 만들 수 있는가? 가능하다면 쉬운 VillagerBench 과제에서 G/G 경로를 먼저 재현한다. 불가능하다면 후보·인자 생성에 필요한 생성형 기능을 분리하거나 교체 범위를 더 좁힌다. 결정을 기록하기 전부터 JEV 모델 구현이나 2×2 전체 실행을 약속하지 않는다.

Benchmark는 기존 Construction을 기준 과제로 유지하고, Farm-to-Table을 주력 **후보**로 선별한다. Escape Room은 동기화·시간 의존성의 후속 후보이며, 에이전트 수에 따라 생성 과제가 바뀌는지 확인해야 한다. 외부 benchmark 이식과 게임 내 에이전트 이질성은 별도 확장 판단이다.

## 문서 경계

- [연구 청사진](MineSkynet_blueprint.md): 현재 질문, 정책 경계, 실험·판정 원칙
- [연구 마일스톤](research_milestone.md): 단계별 통과·중단 기준과 보존할 근거
- [VA 논문–코드 지도](../architecture_understand/VA_code_paper_map.md): TD·AC·SM·BA의 실제 책임
- [랩미팅 초안](../human_report/labmeeting_temp.md): 발표용 논점과 아직 정리 중인 제안
- [리포트 로그](../human_report/report_log.md): 날짜별 실행·진단 및 원시 증거

과거 질문과 당시 판단은 Git 기록·리포트 로그에 남긴다. 이전 완료 사례를 새 정책의 성공으로 소급하지 않는다.
