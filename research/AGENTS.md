# MineSkynet 연구 작업 원칙

이 문서는 루트 [AGENTS.md](../AGENTS.md)의 공통 규칙에 더해 `research/` 문서의 역할과 서술 기준만 정한다. 현재 질문과 다음 결정은 [연구 청사진](doc/blueprint_milestone/MineSkynet_blueprint.md)과 [마일스톤](doc/blueprint_milestone/milestone_index.md)에 둔다.

## 연구 문서의 범위

- 현재 연구 범위와 실험 경계는 루트 지침·청사진을 따른다. `odyssey_legacy/`는 과거 근거이며 현재 질문에 필요한 부분이 확인될 때만 좁게 참조·수정한다.

## 문서별 역할

| 위치 | 무엇을 기록하는가 |
| --- | --- |
| [README.md](README.md) | 처음 읽는 사람을 위한 목적·현재 상태·읽는 순서 |
| `doc/blueprint_milestone/` | 현재 질문·실험 방향과 다음 단계의 완료 기준 |
| `doc/architecture_understand/` | 논문 개념과 공개 코드의 기능별 대응 |
| `doc/idea_hypothesis/` | 아직 검증하지 않은 가설과 이론 탐색 |
| `doc/human_report/report_log.md` | 날짜별 실행·진단 근거와 당시 판단 |
| `doc/human_report/labmeeting_temp.md` | 교수·동료에게 보고할 내용의 임시 초안 |
| `odyssey_legacy/` | 현재 VA 기준선과 구분할 과거 Odyssey 자료 |

같은 결론을 여러 문서에서 독립적으로 관리하지 않는다. 현재 판정은 청사진·마일스톤에 짧게 적고, 상세 과정은 로그와 원시 결과로 연결한다. 과거 보고의 당시 표현을 현재 결론으로 읽지 않는다.

## 연구 서술 규칙

1. **논문과 코드를 대응시킨다.** VA의 Task Decomposer, Agent Controller, State Manager, Base Agent에 관한 설명은 [기능 대응표](doc/architecture_understand/VA_code_paper_map.md)에 연결하고, 논문상 설계와 실제 구현의 차이를 숨기지 않는다.
2. **주장의 근거 수준을 적는다.** 정적 분석, TD/AC 프로브, actor 포함 실행, judger 점수와 반복 비교를 구분한다. Task25 첫 라운드 배정 성공을 전체 과제 성공으로, Task20 한 번의 12/12 완료를 agent 수 효과로 쓰지 않는다.
3. **기록의 소유 문서를 지킨다.** 현재 판정은 청사진·마일스톤, 날짜별 과정과 원시 경로는 보고 로그, 발표용 선별 내용은 랩미팅 초안에 둔다. 같은 결론을 여러 곳에서 독립적으로 갱신하지 않는다.

## 문서 갱신 기준

연구자, 교수·동료, 처음 온 제3자가 상위 문서에서 **목적·확인된 상태·다음 결정**을 바로 파악할 수 있게 쓴다. 과거 완료 내용은 한 줄로 압축하고 상세 근거는 링크로 내린다. 역사적 보고는 당시 판단을 보존하되, 현재와 다른 결론은 최신 문서에서 구분한다.
