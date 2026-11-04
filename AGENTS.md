# VA-MAS 작업 지침

## 프로젝트와 연구 기준

이 저장소는 VillagerAgent(VA) 코드와 MineSkynet 연구 문서를 함께 관리한다. 현재 질문은 **생성형 계획을 유지하면서 Base Agent의 행동 선택과 Agent Controller의 작업 배정을 결정형 정책으로 분리했을 때 성능·시간·추론 비용이 어떻게 달라지는가**이다. BA 단일 축을 먼저 검증하고 AC는 실제 선택 기회가 확인된 뒤 비교한다. TD·AC·상태 관리·actor 실행·judger 점수를 구분한다. 이기종 장치 할당과 Odyssey 이식은 필수 구현이 아니다. 자세한 연구 판단 기준은 [doc/research/AGENTS.md](doc/research/AGENTS.md)를 따른다.

## 디렉터리 지도

| 위치 | 역할 |
| --- | --- |
| `pipeline/` | Task Manager·Controller·Data Manager·Base Agent의 계획·배정·실행 흐름 |
| `type_define/` | `Task`·`Graph` 등 파이프라인이 공유하는 작업 상태·자료 계약 |
| `env/` | Minecraft 접속·행동 API, VillagerBench 실행과 scenario judger |
| `model/` | LLM 공통 인터페이스, 공급자 어댑터, 모델 생성·사용량 기록 |
| `data/` | 건설·농업 등 benchmark 입력과 실행 중 생성되는 상태 JSON |
| `doc/research/` | 연구 질문, 마일스톤, 논문–코드 대응, 실험 보고와 과거 Odyssey 근거 |
| `result/` | 실행별 점수·행동·추론 기록 등 실험 산출물 |
| `logs/`, `img/` | 실행 로그와 생성된 그래프·시각 자료 |
| `ui/logs/` | 모델 어댑터가 기록하는 실행 로그 |
| `doc/` | API 설명·리팩토링·smoke 및 연구 문서 |
| 루트의 `start_with_config.py`, `tiny_start.py`, `td_ac_probe.py`와 `examples/` | Full 실행·최소 예제·actor 없는 프로브와 benchmark 설정 |
| `.venv/`, `node_modules/`, `.runtime/`, `.cache/` | 로컬 환경·서버·캐시; 소스나 연구 근거의 원본으로 취급하지 않음 |

전체 부가 기능은 `archive/full-features-20261104` 브랜치에 보존한다. 핵심은 Gemini·Ollama·Tev1, Full Controller, Construction·Farming·Escape이며 제거한 기능으로 fallback하지 않는다. 이상점은 귀속 보고서에 기록하고 동작 변경은 별도 판단으로 둔다.

하위 지침은 `pipeline/`, `type_define/`, `env/`, `model/`, `data/`, `doc/research/`의 `AGENTS.md`에만 둔다. 각 파일은 해당 디렉터리의 고유한 경계만 추가하며, 공통 규칙을 반복하지 않는다.

## 코딩 스타일과 설계 패턴

- 연구에 연결되는 변경은 구현 설명보다 먼저 해당 기능이 보존·검증하는 논문 개념과 질문을 한 문장으로 밝힌다. 논문 설명과 실제 코드 동작이 다르면 둘을 구분한다.
- 기존 공개 코드 전체를 스타일 통일 목적으로 재작성하지 않는다. **새로 작성하거나 수정하는 코드**는 주변 인터페이스를 유지하고 Python `snake_case` 함수·변수, `PascalCase` 클래스를 사용한다. 새 공개 함수에는 입력·반환 타입과 실패 조건을 드러낸다.
- 계획(TD), 배정(AC), 상태 관리, actor 실행, 최종 채점을 서로 다른 책임으로 유지한다. Base Agent의 reflection을 benchmark judger 점수와 동일시하지 않는다.
- 새 LLM 공급자는 `model/`의 공통 인터페이스와 생성 경로를 통해 연결한다(어댑터·팩토리 패턴). 공급자별 인증·파싱·가격 처리를 Controller나 actor 곳곳에 복제하지 않는다.
- LLM 제안은 곧바로 실행하지 않는다. `Task`·`Graph`의 선행조건, 후보 agent, 가용성, 응답 형식 등 결정적 제약을 검증한 뒤 배정한다. `Graph.add_edge()` 자체는 순환을 검사하지 않으므로 DAG 알고리즘을 적용하기 전에 별도 검증한다.
- 새 비교 정책이 필요하면 기존 경로를 조용히 바꾸지 말고 정책 선택을 명시해 기준선과 대조군을 분리한다(전략 패턴). 서버·bot·judger의 시작/종료는 `VillagerBench.run()` 같은 수명주기 경계에서 관리한다.
- 새 코드에서 불필요한 전역 상태, wildcard import, import 시 네트워크 호출·서버 기동·파일 초기화를 늘리지 않는다. 공유 상태를 여러 스레드가 바꾸는 경우 동기화 책임과 로그의 시점을 분명히 한다.

## 실험·검증 규칙

- 먼저 정적 확인이나 오프라인 fixture를 사용한다. `td_ac_probe.py --self-test`는 API·Minecraft 없이 검사하며, `--live`는 외부 API를 사용하지만 actor·Minecraft 실행을 대신하지 않는다. 실제 서버·API·benchmark 실행은 요청 범위와 비용을 확인한 뒤 진행한다.
- `VillagerBench` 초기화와 일부 Task Manager 경로는 `data/score.json`, `logs/`, 생성 그래프 등을 초기화·삭제할 수 있다. 새 실행 전 필요한 기존 원시 증거를 실행별 `result/` 경로에 보존했는지 확인한다. 다른 실험의 결과 폴더를 덮어쓰지 않는다.
- 결과에는 코드 commit, 과제·agent 수, 모델·Controller 경로, 월드·난이도·스폰, 반복 번호, 점수·호출량·비용, 원시 로그 경로를 남긴다. 정적 분석, TD/AC 프로브, actor 포함 실행, judger 점수, 반복 비교를 구분한다.
- 코드·모델·프롬프트·월드·채점 조건을 바꾼 실행은 같은 조건의 반복으로 합치지 않는다. 실패와 미관찰도 기록하며, 한 사례의 상관관계를 특정 병목의 인과 증거로 승격하지 않는다.

## 금지와 의사결정 경계

- API 키·인증 정보·원시 프롬프트의 민감한 내용을 코드, 문서, 공유 로그에 남기지 않는다. 외부 서비스 응답과 비용은 필요한 범위에서만 기록한다.
- 연구 질문, 주 지표, 성공 기준, 비교군을 바꾸는 결정은 근거와 선택지를 제시하고 연구자가 정한다. 검증 목적을 벗어난 대규모 VA 디버깅이나 Odyssey 현대화를 임의로 시작하지 않는다.
- 사용자·연구자가 만든 기존 변경과 결과를 보존한다. 실행 환경을 재생성하거나 기존 로그·월드를 지우는 작업은 정확한 대상과 영향 범위를 확인한다.
