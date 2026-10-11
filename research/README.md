# MineSkynet 연구 안내

이 폴더는 VillagerAgent(VA)를 기준 시스템으로 삼아 Minecraft 다중 에이전트의 협업 효율을 연구하는 문서 공간이다. 현재 질문은 **에이전트 수가 늘 때 작업 효율과 에이전트당 효율이 왜 둔화하거나 감소하는가**이다. 우선 계획·배정·실행 단계별 원인을 식별하고, 재현된 병목에 한해 개선안을 비교한다. 이기종 하드웨어별 작업 배정과 Odyssey 이식은 현재의 주 실험 목표가 아니다.

## 먼저 읽을 문서

1. [연구 원칙](AGENTS.md): 주장·증거 수준과 문서 작성 기준
2. [연구 청사진](doc/blueprint_milestone/MineSkynet_blueprint.md): 질문, 가설, VA 구조 및 실험 설계
3. [마일스톤 인덱스](doc/blueprint_milestone/milestone_index.md): 확인된 범위와 다음 결정
4. [연구 마일스톤](doc/blueprint_milestone/research_milestone.md): 단계별 완료 기준

문서는 목적에 따라 나뉜다. `blueprint_milestone/`은 현재 질문·계획, `architecture_understand/`는 논문–코드 대응, `idea_hypothesis/`는 아직 검증하지 않은 가설·개념 메모, `human_report/`는 날짜별 기록과 발표 초안이다. 자세한 논문–코드 대응은 [VA 구조 지도](doc/architecture_understand/VA_code_paper_map.md), 실험 경과는 [리포트 로그](doc/human_report/report_log.md), 다음 랩미팅용 초안은 [임시 보고](doc/human_report/labmeeting_temp.md)를 본다. [OS·DAG 메모](doc/idea_hypothesis/os_nw_DAG_note.md)는 개념 탐색 자료이며, 이론적 연결이나 원인 판정이 끝났다는 뜻이 아니다. [Odyssey 관련 대응표](doc/architecture_understand/paper_code_dependency_map.md)는 과거 경로를 확인할 때만 참조한다.

## 현재 확인된 범위

- VA의 원본 `controller.py`를 사용한 작은 Construction 과제(Task0·1인, Task6·3인)를 검증했다.
- 평지·Peaceful 월드의 Task20·3인 재실행에서, actor 출력 한도와 파서·피드백 기록을 개선한 뒤 최종 점수는 **12/12 블록, `complete task`**였다. 이는 해당 실행의 완료이지 에이전트 수에 따른 병목 원인 규명은 아니다. 근거: [Task20 점수](../result/gemini-3.8-flash_construction_task20_3p_controller_llm_flat_20261007_trial2_feedback1024/score.json).
- [Task25 TD/AC 프로브](../result/td_ac_probe_task25_20261007/probe.json)는 실제 actor·Minecraft 실행 없이 첫 계획과 배정만 확인했다. 노드 3개·간선 0개, 명시된 블록 9/15개이며 세 배정은 유효했다. 첫 라운드 부분 계획을 전체 계획 실패로 해석하지 않는다.
- Task50은 다음 계획·배정 프로브 후보일 뿐, 선행 간선이나 병목이 실제로 생성됐다는 증거는 아직 없다.

## 실행 환경과 재현 기록

이 저장소 루트는 `MineSkynet-VA`이고 Python 환경은 루트의 Conda prefix `.venv`이다. 저장소 루트의 [원본 VA README](../README.md)는 일반 사용법 참고용이며, 현재 연구의 실험 조건·완료 판정은 이 폴더의 문서와 개별 결과 파일을 우선한다. 계획·배정만 볼 때는 [`td_ac_probe.py`](../td_ac_probe.py), benchmark 실행 경로는 [`start_with_config.py`](../start_with_config.py)와 [`agent_demo.py`](../agent_demo.py)를 확인한다. 실행 명령·API 설정은 선택한 과제와 서버 상태를 확인한 뒤 기록에 맞춰 사용한다.

실험을 비교할 때는 코드 commit, model·설정, 월드 종류·난이도·스폰, 과제, 에이전트 수, Controller 경로, 반복 번호, API 사용량, 원시 로그와 score 경로를 함께 남긴다. VA의 Base Agent reflection과 benchmark judger 점수는 서로 다른 판정이므로 혼용하지 않는다. API 키는 저장소나 연구 문서에 적지 않는다.

## 현재 범위 밖

Odyssey actor 이식, lifelong memory, 물리 장치별 성능 라우팅, cloud-only/edge-only 비교는 후속 가능성으로 보류한다. 현재 원인도 확인되지 않은 상태에서 이들을 필수 구성이나 이미 검증된 기여로 다루지 않는다. 과거 Odyssey 현대화 계획의 위치는 [보류 범위 메모](doc/blueprint_milestone/modernization_milestone.md)에 짧게 남긴다.
