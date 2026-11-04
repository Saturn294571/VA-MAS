# RQ 핵심과 전체 기능 보존 경계

2026-11-04 연구자가 생성형 계획을 유지한 BA 행동 선택·AC 배정의 결정형 정책 분리 비교를 현재 RQ로 확정했다. BA 단일 축을 먼저 검증하고 AC는 실제 선택 기회를 확인한 뒤 비교한다. 세 benchmark를 남기고 Full Controller만 유지하며, 과거 이상점은 이번에 수정하지 않는다.

## 브랜치와 보존 범위

- 전체 기능 보존: `archive/full-features-20261104`, 체크포인트 **`ea1e9c766107713419fd0fe784a237d2508cd3f1`**.
- 핵심 정리: `refactor/project-structure`; 검증 후 main에 fast-forward 반영한다. 원격 push는 하지 않는다.
- 보존 체크포인트에는 사용자 연구 문서 이동·링크 갱신, Gemini 3.1 smoke 지원·보고, Node 설치 잠금파일과 기존 선택 기능이 함께 들어 있다.
- 환경·Node 설치물·월드·인증·ignored 원시 결과는 Git에 강제 추가하지 않았다. 기존 위치와 해시를 보존한다. 브랜치는 코드·문서·입력·잠금파일의 보존이며, 실행하지 않은 모든 부가 기능의 정상 동작 보증은 아니다.

[기계 판독 목록](core_separation_evidence.json)에 checkpoint, 제거 파일 33개, 유지 함수 비교와 검증 결과를 기록한다. [과거 이상점 귀속](historical_anomalies_2026-11-04.md)은 이 기능 분리와 별도 근거다.

## 유지·분리한 책임

| 기능 | 핵심 main | 보존 브랜치 |
| --- | --- | --- |
| TD·SM·Task·Graph·Full AC·BA·trace | 유지 | 유지 |
| Gemini·Ollama 역할별 생성형 모델 | 유지 | 유지 |
| Tev1·hybrid·반복 배치와 공통 행동/배정 계약 | 유지 | 유지 |
| Construction·Farming·Escape와 입력 자산 | 유지 | 유지 |
| Tiny Start 최소 예제·TD/AC 프로브 | 유지 | 유지 |
| 별도 Tiny Controller | 제거, `tiny` 설정 거부 | 유지 |
| RL·VLLM 전용 actor·추가 공급자 | 실행 분기·import까지 제거 | 유지 |
| Meta·자동 과제 생성·감시·수동 actor 예제 | 제거 | 유지 |
| FastAPI 대안 서버·과거 검색·학습 자료 가공·Docker | 제거 | 유지 |
| 연구 기록·문헌·기존 결과·baseline 프롬프트/공통 행동 도구 | 보존 | 보존 |

`tiny_start.py`는 Full을 사용한다. 공통 행동 API와 speaking style은 핵심의 baseline 프롬프트 및 세 benchmark 실행에 연결되어 있으므로 기능명만 보고 삭제하지 않았다. Escape의 `minecraft_define`도 실제 생성·채점 의존성이다.

## 의존성 차단

- 파이프라인에서 추가 공급자의 클래스 import·분기를 제거하고 BaseAgent의 타입은 `AbstractLanguageModel`로 표현한다. Gemini/Ollama가 이전에 통과하던 실행·프롬프트 분기를 그대로 남긴다.
- 모델 팩토리와 actor는 Gemini/Ollama만 받는다. Python `openai`는 Gemini endpoint에 필요하므로 유지한다. unknown provider, GPT·GLM·VLLM 등의 구식 모델 선택은 보존 브랜치를 안내하는 오류로 거부한다.
- Full만 생성하며 `controller_mode` 생략 기본값은 `full`이다. `tiny`를 조용히 Full로 바꾸지 않는다.
- Meta·자동 생성 환경과 FastAPI 선택은 runtime 생성·bot 기동 전 거부한다. 삭제한 파일을 호출하는 subprocess 경로를 남기지 않는다.
- 기본/Construction 설치 목록만 남긴다. 임베딩 캐시가 없는 Construction의 `FlagEmbedding`은 실제 사용되므로 선택 의존성으로 유지한다.
- 보존 브랜치의 코드를 같은 작업 폴더에 복제하지 않고 과거 프로젝트를 `sys.path`·`PYTHONPATH`·fallback으로 연결하지 않는다.

## 검증과 해석

보존 체크포인트의 오프라인 runner 8항목이 통과했다. 핵심에는 세 benchmark의 실행 구성·judger subprocess 인자, 제거 설정의 초기 거부, reflection의 실제 action history 반영, 기존 환경 예외 처리의 정상 반환을 검사하는 fixture를 추가했다. 생성형/결정형 행동·역할별 모델·배정 계약·trace의 기존 검사도 유지한다.

실제 유료 모델·게임 재실행은 하지 않는다. 이전 smoke는 이전 코드·조건의 증거로 보존하며 이번 정리를 동일 조건의 반복 실험으로 합치지 않는다. 깨끗한 checkout 검증 결과와 최종 main 반영 여부는 아래 완료 기록에 적는다. 기존 전체 `.venv`에 선택 패키지가 남아 있어도 검사에서는 제거 모듈·SDK의 import를 차단해 숨은 의존성을 드러낸다.

## 완료 기록

검증 및 main 반영 후 확정한다.
