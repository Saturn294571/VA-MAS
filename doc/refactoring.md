# VA-MAS 구조 리팩토링 기록

## 목적과 기준점

VA 논문의 TD·AC·상태 관리·BA와 환경 judger를 구별하고, 각 단계의 시간·호출·배정·행동 근거를 보존하면서 중복 구현과 기본 실행의 선택 의존성을 줄인다. 논문 개념과 실제 코드 차이는 기존 [기능 대응표](../research/doc/architecture_understand/VA_code_paper_map.md)에 따른다. 이 작업은 정책 성능이나 scaling 원인을 검증한 실험이 아니다.

- 날짜: 2026-11-04
- 저장소: `Saturn294571/VA-MAS`
- 기준 commit: `03737a8` (`before github repository migration`)
- 브랜치: `refactor/project-structure`
- 시작 시 작업 트리는 깨끗했다. 기준점은 로컬 remote-tracking ref로 확인했고 원격 fetch는 하지 않았다.
- 루트 지침의 scaling 원인 귀속 질문과 연구 문서의 생성–결정 역할 분리 질문은 다르다. 리팩토링에서 연구 질문·성공 기준·비교군을 선택하거나 변경하지 않았다.

## 구현과 호환 경계

| 부분 | 변경 | 보존한 동작 |
| --- | --- | --- |
| 로깅·파싱 | `common`으로 추출 | 기존 유틸리티 import, logger 형식·파일명, 파싱·YAML 대체 처리 |
| 파싱 오류 | 원시 응답 출력 대신 예외 종류만 기록 | pipeline parser의 오류 전파와 model parser의 실패 시 `[]` 반환 차이 |
| 과거 검색 함수 | `pipeline.legacy_retrieval`로 분리, 기존 함수는 지연 import | 함수명·인자·반환 경로. 기존 `TaskManager`의 Retriever는 유지 |
| 미사용 코드 | `agent_save.py`, 두 요약 자료형, 사용하지 않는 DataManager import 제거 | 활성 호출이 없는지 소스·문서·동적 import 문자열 검색. Document 변환은 명시적 import로 유지 |
| 모델 팩토리 | 선택 어댑터만 import | 모델명 판별 순서, provider·역할 설정과 생성 인자. VLLM 설정 dict 출력은 인증 노출 방지를 위해 제거 |
| RL·임베딩 | RL public 클래스·Construction 임베딩 지연 import, BA의 불필요한 RL·torch import 제거 | 선택 시 기존 구현 사용, 누락 패키지는 설치 목록을 포함한 오류 |
| 모델 기록 | Gemini/Ollama의 초기화·동일 thread lock을 `model.runtime_usage`로 이동 | `data/tokens.json` 필드, 기존 파일 생성, 집계·가격 계산, Ollama 비용 `None`, 누락 usage 기록 |
| 실행 구성 | benchmark 실행기도 기존 actor 설정 함수를 사용 | 설정 키·기본값, 역할별 공급자 선택. Ollama actor에는 불필요한 Gemini 인증을 전달하지 않음 |
| Controller | 내부 `ControllerExecution`에 초기화·worker 루프·조회·상태 반영·run 공통화 | 두 public `GlobalController` 경로·생성자, 모델 공유 방식, 배정 정책, thread 수·poll 간격·결과 순서 |
| 환경 선언 | 기능별 requirements와 Git/Docker 제외 규칙 | 기존 pin·전체 기능 설치 목록. 실제 설치·버전 해석은 미검증 |

Full은 시간·성공/실패 예산, 다중 agent 배정과 제출 후 대기를 유지한다. Tiny는 직접 배정과 worker 내부의 기존 큐 처리·로그 동작을 유지한다. Full/Tiny를 하나의 배정 정책으로 합치지 않았다. Task 상태와 reflection의 기존 표현도 그대로다.

이전 모델 어댑터 전체의 cache·usage 기록을 재작성하지 않았다. 공통 token lock은 이전과 같은 **프로세스 내부 thread lock**이며 프로세스 간 동기화를 새로 보장하지 않는다. 초기화는 import 시 수행하지 않는다. Ollama에서도 이전 초기화와 동일한 파일 집합을 만들도록 `google.logs` 생성까지 보존했다.

기존 `data/`, `logs/`, `ui/logs/`, `.cache/`, `result/` 경로는 바꾸지 않았다. 과거 결과는 이번 리팩토링의 새 반복 실험으로 합치지 않는다. RL·자동 과제 생성·FastAPI·기존 공급자·Ollama·Tev1은 남아 있다. 선택 기능은 해당 [설치 목록](../README.md#설치와-선택-기능)을 명시적으로 설치한다.

## 검증 방법과 결과

새 체크아웃에는 환경이 없어, 이미 존재하던 `MineSkynet-VA/.venv/bin/python`(Python 3.10.20)을 사용했다. 패키지 설치나 환경 재생성은 하지 않았다. 검사에는 fixture·mock 응답을 사용했고 Minecraft·Ollama·외부 API를 호출하지 않았다.

공통 실행 명령:

```bash
/path/to/existing/python -B verification/run_offline.py --report /tmp/va-refactor-checks.json
```

runner는 각 검사를 별도 임시 작업 디렉터리에서 실행하고 socket 연결을 차단하며, TD/AC 프로브에도 임시 `--output`을 지정한다. 보고서는 지정한 파일에만 쓴다. 의존성 경계 검사의 하위 프로세스는 선택 SDK를 차단하고 import 시 `data`·cache·로그·결과 폴더를 만들지 않는지 확인한다.

| 검사 | 변경 전 관찰 | 변경 후 |
| --- | --- | --- |
| assignment 계약 | 통과 | 통과 |
| hybrid placement | 통과 | 통과 |
| Ollama 역할·actor·launcher | 17개 중 launcher fixture 1개 오류 | fixture의 저장소 경로와 필수 정책 설정 보완 후 통과 |
| repeated placement | 통과 | 통과 |
| tracer | 통과 | 통과 |
| TD/AC self-test | 2 node·1 edge·ready 0·Alice 배정, 요청 0 | 같은 결과, 요청 0 |
| 새 구조 검사 | 해당 없음 | 9개 통과: 파싱·의존성·팩토리·문서 변환·Controller·공통 집계 |

초기 baseline runner에서 프로브의 기본 출력이 저장소 `result/`를 사용함을 확인해, 새로 생성된 해당 산출물만 `/tmp`로 옮기고 이후 runner에 명시적 출력 경로를 넣었다. 기존 입력·결과 파일 21개는 SHA-256으로 보존 여부를 확인했다. 기존 파일을 덮어쓰지 않았다.

최종 runner의 7개 검사 항목이 모두 통과했다. unittest 기반 검사 35개, 두 행동 assertion 스크립트와 TD/AC 프로브를 포함한다. Python 파일 77개의 구문 확인과 `git diff --check`도 통과했다.

기존 검사에서 JavaScript bridge 종료 시 resource warning과 일부 의존성 deprecation warning이 관찰된다. 이번 리팩토링에서 이 경고를 해결하거나 새 성능 주장에 사용하지 않았다. Ollama fixture의 초기 실패는 현재 디렉터리를 repo root로 가정했기 때문이며, 이를 바로잡자 현재 launcher의 필수 `decision_policies` 누락이 드러났다. 실행기 검증을 완화하지 않고 fixture를 현재 계약에 맞췄다.

새 구조 검사는 다음을 확인한다.

- 정상·중첩·누락 쉼표·YAML 응답, 무효 응답에서 호출 경로별 실패 동작과 비밀 문자열 비출력.
- 선택 SDK 없는 기본 import와 RL·Construction·Hugging Face 선택 시 설치 안내 오류.
- judger가 사용하는 `env/utils.py`의 직접 import와 DataManager 문서 변환.
- 팩토리의 기존 공급자 판별과 설정 비변경.
- Full/Tiny의 worker 종료·제출 수·대기 차이, offline 처리, 시간·실패·성공 예산.
- Task 상태·reflection 반영, 중단 시 참조·executor 정리.
- Gemini/Ollama 공유 lock, 누적 token·요청 수·금액과 누락 usage 처리.

## 남은 범위

새 환경 설치, optional 기능의 실제 실행, Minecraft actor 포함 완주, 서버·judger 점수, 반복 성능·비용 비교는 검증하지 않았다. 오프라인 통과는 동일 benchmark 성능의 증거가 아니다. requirements 버전·잠금파일 생성 및 Docker 빌드도 미검증이다. Dockerfile은 아직 존재하지 않는 `run.py`를 가리킨다.

결과 저장 경로 전환, 입력 자산 분할·압축, 이미지·논문 삭제, 연구 문서 통합, FastAPI 서버 현대화, 모든 모델 어댑터의 기록 체계 통합은 후속이다. 기존 환경·로그·월드나 연구 자료는 정리 대상으로 삭제하지 않았다. 원격 push와 PR 생성은 하지 않는다.
