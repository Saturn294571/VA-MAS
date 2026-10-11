# 실행 기반과 보류한 현대화 작업

최종 갱신: 2026-10-12

문서 상태: 과거 Odyssey 현대화 마일스톤을 대체한 **범위 메모**. 파일 경로는 기존 링크를 위해 유지한다.

## 현재 재현 기반

연구의 기준 시스템은 이 저장소의 **VillagerAgent**이다. 재현 작업의 목적은 Odyssey를 새로 완성하는 것이 아니라, VA의 TD → AC → Base Agent → State Manager·judger 경로를 비교 가능한 조건으로 실행하고 로그로 분리하는 것이다. 구체적인 실험 완료 기준은 [연구 마일스톤](research_milestone.md)에만 둔다.

현재 확인된 것은 원본 Controller를 통한 작은 Construction 경로, 평지·Peaceful 월드에서 Task20 한 실행의 12/12 완료, Task25 첫 라운드의 actor 없는 TD/AC 프로브다. 이들은 각각 **end-to-end 실행**, **benchmark 완료 사례**, **계획·배정 component 검사**로 증거 범위가 다르다. VA 원 논문의 전체 benchmark 재현이나 agent 수 증가의 원인 검증 완료는 아니다.

실험 기반을 바꿀 때는 Minecraft 버전·월드·스폰·난이도, Python/Node 환경, model·API, actor 출력 한도, 파서·피드백, Controller 경로와 코드 commit을 기록한다. 원시 실행과 [리포트 로그](../human_report/report_log.md)를 연결하고, 수정 전후 실행을 같은 조건의 반복으로 합산하지 않는다.

## Odyssey의 현재 지위

Odyssey는 초기에 actor service와 lifelong in-context 구상을 검토하던 선행연구다. 현 연구의 TD·AC·State Manager를 대체하거나 VA 재현의 선행 조건으로 두지 않는다. 구형 의존성 현대화, 40 primitive·183 skill, semantic retrieval, MineMA actor와 별도 branch/profile 완료를 **현재 마일스톤에서 제외**한다. 과거 작업의 상세 근거는 [Odyssey 논문–코드·의존성 대응표](../architecture_understand/paper_code_dependency_map.md) 및 Git 기록에 남아 있다.

장차 actor 계층의 명확한 결함이 현재 질문의 핵심 원인으로 확인되고 VA actor만으로 대조가 불가능할 때, Odyssey의 분리 가능한 기능을 좁게 재검토할 수 있다. 그 경우에도 TD·AC·State Manager의 소유권, 의존성 경계, 기준선과 추가 비용을 별도 설계로 정해야 한다. 지금은 이 결정을 선제적으로 확정하지 않는다.
