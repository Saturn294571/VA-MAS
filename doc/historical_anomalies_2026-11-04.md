# 과거 프로젝트와 리팩토링 이후 이상점 귀속

검증 질문은 관찰된 이상점이 리팩토링 전부터 존재했는지, 새 모델·셋업 조건에서 처음 드러났는지를 구별하는 것이다. 이 보고서는 로그·소스의 정적 비교이며 정책 품질 비교나 인과 실험이 아니다. 이번 핵심 분리에서는 아래 동작을 수정하지 않았다.

## 조사 대상

- 과거 프로젝트: `/home/pluto2479/Documents/MineSkynet-VA`; 조사 시 과거 저장소 HEAD는 `c0687ed`였다. 과거 프로젝트는 읽기만 했다.
- 현재 비교 시점: 전체 기능 보존 체크포인트 `ea1e9c7`, 브랜치 `archive/full-features-20261104`. 이 체크포인트는 리팩토링과 Gemini 3.1 Flash-Lite smoke 변경을 포함한다.
- 과거 `result/`, `logs/`, `ui/logs/`, `data/history/`와 공급자 로그에서 텍스트 산출물 813개를 조사했다. actor termination 기록은 165개(`stop` 164, `length` 1)이며 run ID도 165개다. 서로 다른 과제·조건·복사된 보고를 독립적인 반복 실험으로 집계하지 않는다.
- [기계 판독 근거](historical_anomalies_evidence.json)에 과거 trace 경로, 관련 함수·파일 SHA-256, 길이 종료와 미종료 요청 목록을 둔다. 원시 프롬프트와 인증 내용은 복사하지 않았다. 전체 조사 파일 인덱스는 로컬 `.cache/core-separation/historical_audit.json`에만 있으며 공개 근거에는 인덱스 해시를 남긴다.

## 항목별 결론

| 관찰 | 과거 근거 | 귀속 |
| --- | --- | --- |
| `MALFORMED_FUNCTION_CALL`과 빈 actor 응답 | 조사한 813개 파일에서 해당 문자열은 발견되지 않았다. 과거 actor termination 165개에도 없다. Gemini actor 생성·호출 함수 및 Minecraft client 전체는 분리 전 현재 체크포인트와 동일하다 | **새 조건에서 처음 관찰, 원인 미확정**. Gemini 3.8 Flash → 3.1 Flash-Lite 변경, 프롬프트·월드·Node 셋업 차이가 섞여 있어 리팩토링 원인이라고 단정할 수 없다 |
| SM·actor의 `length` | `20261028_hybrid_tev1_task20_3p_run1/trace/events.jsonl` 등에 SM length가 있고, `20261028_tev1_construction_task20_3p_trial1/actor_llm_requests.jsonl`에는 actor length도 있다 | 기존 현상. 이번에 새로 생긴 출력 상한 정책이 아님 |
| 완료 시 진행 중인 요청 | 과거 trace 9개에서 request start가 end보다 많다. 과거 Task0 retry는 start 26/end 25, 당시 BA 한 요청이 미종료다 | 기존 launcher 종료·계측 경계. 현재 Full start 15/end 14를 새 회귀로 볼 근거 없음 |
| Tiny 하위 작업 1회 종료 | 과거 `tiny_start.py`도 성공/실패 횟수 제한이 각각 1이다. 과거 Tiny 기록에는 talkTo·waitForFeedback이 있어 당시에는 첫 하위 작업이 대화였다 | 기존 종료 조건. 첫 하위 작업이 탐색이면 상위 대화 목표 전에 끝날 수 있음 |
| 실패인데 정상 exit 가능 | 과거와 현재 `VillagerBench.run()`의 예외 처리 함수가 동일하고 예외를 기록한 뒤 다시 던지지 않는다. 실패 횟수 종료도 예외 종료가 아니다 | 기존 코드 구조. 과거의 같은 빈 모델 응답에서 exit 0이 실제 발생했다고까지 주장하지 않음 |
| 1인 Full Task0의 직접 배정 | 과거 `20261028_005349_construction_task0_1p_full_controller_contract_smoke_retry1/summary.json`은 direct 4회다. 현재도 후보가 필요 인원과 같아 direct 경로를 사용한다 | 기존 설계·과제 특성. AC LLM이 호출되지 않았다는 사실을 숨기지 않아야 함 |
| 큰 efficiency | 과거 Task0 score의 efficiency는 43.431488, use_time 7초이며 현재는 101.340139/3초다. judger와 `calculate_action_time()`은 분리 전 비교에서 동일하다 | 기존 산식. 0~1 완료율·백분율이나 총 wall-clock 속도 향상으로 읽으면 안 됨 |

과거 로그 부재는 발생하지 않았다는 증명이 아니다. 모델·코드·프롬프트·상태를 고정한 대조 실행 없이 빈 응답의 원인을 공급자나 리팩토링 하나에 귀속하지 않는다. 추가 유료 API·서버 실험은 수행하지 않았다.

## 리팩토링과 핵심 분리의 구분

과거와 리팩토링 체크포인트 비교에서 `env/minecraft_client.py`, `env/env.py`, `env/build_judger.py`는 파일 전체가 동일했다. Gemini의 `create_google_chat_model()`, `_new_client()`, `few_shot_generate_thoughts()`도 AST가 동일했다. Gemini 3.1 지원 목록·가격과 공통 기록 모듈 이동은 별도 차이로 기록한다.

이후 RQ 핵심 분리에서 구식 공급자 분기·RL·VLLM·Tiny Controller 등을 제거했다. Gemini/Ollama가 실제 사용하던 else 분기를 남겼으며, 공통 타입으로 `isinstance`를 바꿔 다른 프롬프트 경로로 전환하지 않았다. 유지 함수 12개의 AST를 보존본과 비교해 일치를 확인했다. 이는 소스 동작 보존 근거이며 새로운 actor 포함 완료 실험은 아니다.

## 후속 판단

빈 응답의 오류 판정, 상위 목표 완료와 하위 작업 종료의 구분, 프로세스 exit code, 종료 시 진행 중 호출 표시, SM 출력 상한 조정은 후속 변경으로 남긴다. 각각의 수정은 baseline 정책과 계측 의미를 바꿀 수 있으므로 별도 조건·검증으로 다룬다. 현재 핵심과 보존 브랜치 모두에 실패 사례의 증거를 남긴다.
