# MineSkynet 연구 안내

이 폴더는 VillagerAgent(VA)를 기준 시스템으로 삼아 Minecraft 다중 에이전트의 **생성형 추론과 제한된 결정의 역할 분리**를 연구하는 문서 공간이다. 현재 질문은 고수준 계획을 유지한 채 Base Agent(BA)의 다음 행동 선택과 Agent Controller(AC)의 작업 배정을 각각 경량 결정 정책으로 바꿀 때 **과제 성능·실행 시간·추론 비용이 어떻게 달라지는가**이다. BA 행동 선택을 먼저 비교하고, AC 배정은 실제 선택 기회가 확인된 뒤 다룬다. 에이전트 수 증가의 모든 효율 저하 원인 규명은 현재 필수 목표가 아니다.

## 먼저 읽을 문서

1. [연구 원칙](AGENTS.md): 주장·증거 수준과 문서 작성 기준
2. [연구 청사진](doc/blueprint_milestone/MineSkynet_blueprint.md): 현재 질문, 생성형/결정형 비교 축과 판정 경계
3. [마일스톤 인덱스](doc/blueprint_milestone/milestone_index.md): 확인된 범위와 다음 결정
4. [연구 마일스톤](doc/blueprint_milestone/research_milestone.md): 단계별 완료 기준

문서는 목적에 따라 나뉜다. `blueprint_milestone/`은 현재 질문·계획, `architecture_understand/`는 논문–코드 대응, `idea_hypothesis/`는 검증 전 가설·개념 메모, `human_report/`는 날짜별 기록과 발표 초안이다. 자세한 논문–코드 대응은 [VA 구조 지도](doc/architecture_understand/VA_code_paper_map.md), 실험 경과는 [리포트 로그](doc/human_report/report_log.md), 다음 랩미팅용 논점은 [임시 보고](doc/human_report/labmeeting_temp.md)를 본다. [OS·DAG 메모](doc/idea_hypothesis/os_nw_DAG_note.md)는 이전 병목 질문의 개념 탐색 자료이며 현재 필수 이론 과제가 아니다. [Odyssey 관련 대응표](doc/architecture_understand/paper_code_dependency_map.md)는 과거 경로를 확인할 때만 참조한다.

## 현재 확인된 범위

- VA의 원본 `controller.py`를 사용한 작은 Construction 경로를 확인했다. 평지·Peaceful 월드의 Task20·3인 한 실행은 actor 출력·파서·피드백 개선 후 **12/12 블록, `complete task`**로 끝났다. [Task20 점수](../result/gemini-3.8-flash_construction_task20_3p_controller_llm_flat_20261007_trial2_feedback1024/score.json)
- [Task25 TD/AC 프로브](../result/td_ac_probe_task25_20261007/probe.json)는 합성 snapshot에서 첫 계획·배정만 확인했다. 노드 3개·간선 0개, 첫 라운드 명시 블록 9/15개와 유효 배정 3개였으며 actor 실행·전체 과제 완료는 검사하지 않았다.
- **생성형/결정형 정책을 공통 계약으로 비교한 결과는 아직 없다.** Farm-to-Table은 주력 benchmark 후보, Construction은 기존 기준 과제, Escape Room은 후속 후보이다. BA 행동 선택의 경계·유효한 행동 및 인자 집합을 확인하는 것이 다음 단계다.

## 실행 환경과 재현 기록

이 저장소 루트는 `MineSkynet-VA`이고 Python 환경은 루트의 Conda prefix `.venv`이다. 저장소 루트의 [원본 VA README](../README.md)는 일반 사용법 참고용이며, 현재 연구의 실험 조건·완료 판정은 이 폴더의 문서와 개별 결과 파일을 우선한다. 계획·배정만 볼 때는 [`td_ac_probe.py`](../td_ac_probe.py), benchmark 실행 경로는 [`start_with_config.py`](../start_with_config.py)와 [`agent_demo.py`](../agent_demo.py)를 확인한다. 실행 명령·API 설정은 선택한 과제와 서버 상태를 확인한 뒤 기록에 맞춰 사용한다.

실험을 비교할 때는 코드 commit, model·설정, 월드 종류·난이도·스폰, 과제, 에이전트 수, AC/BA 정책, 반복 번호, 역할별 호출·비용, 원시 로그와 score 경로를 함께 남긴다. 현행 정책을 공통 계약으로 감싼 G/G, BA 행동 선택만 바꾼 G/D, AC 배정만 바꾼 D/G, 둘 다 바꾼 D/D는 **서로 다른 조건**이다. 행동당 결정 지연과 전체 과제 완수 시간을 구분하고, fallback·무효 행동을 숨기지 않는다. VA의 BA reflection과 benchmark judger 점수도 혼용하지 않는다. API 키는 저장소나 연구 문서에 적지 않는다.

## 현재 범위 밖

Odyssey actor 이식, lifelong memory, 물리 장치별 성능 라우팅, cloud-only/edge-only 비교, 새 benchmark 제작과 기존 scaling 저하의 포괄적 인과분해는 현재 필수 범위가 아니다. 특정 JEV류 또는 로컬 모델도 아직 확정하지 않았다. 과거 Odyssey 현대화 계획의 위치는 [보류 범위 메모](doc/blueprint_milestone/modernization_milestone.md)에 남긴다.
