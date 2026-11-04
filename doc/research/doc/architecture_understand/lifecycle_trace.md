# VA lifecycle trace

목적은 생성형/결정형 정책 비교에서 계획·배정·상태 관리·actor 실행의 시간과 호출량을 과제 결과와 함께 살피는 것이다. 계측은 기존 작업·평가 정책의 대체가 아니다.

## 생성 위치와 사용

`start_with_config.py`로 새 과제를 실행하면 기존 `task_name`에 해당하는 `result/<task_name>/`에 다음 파일을 만든다. 같은 이름의 결과는 기존 launcher의 검사에 따라 건너뛴다. 실험 설정에 날짜·과제·인원·정책·반복을 포함한 고유한 `task_name`을 지정한다.

```text
result/<task_name>/
├── manifest.json       # 허용된 설정, commit, dirty 여부, 미기록 환경 조건
├── trace/events.jsonl  # 진행 중 즉시 추가하는 이벤트
├── summary.json        # 부모 프로세스가 종료 후 생성한 집계
├── score.json          # 기존 judger의 결과가 생성된 경우
└── ...                 # 기존 actor 이력과 결과
```

기존 `data/`·`logs/`는 VA가 사용하는 실행 중 작업 공간이다. tracer는 이를 정리하거나 이전 결과를 옮기지 않는다. `research/log/`도 사용하지 않는다. `result/`는 현재 Git 제외 대상이므로 보존·공유 방법은 별도로 관리한다.

부모 프로세스까지 강제로 종료되어 요약이 없다면 raw trace로 복구할 수 있다.

```bash
.venv/bin/python tracer.py result/<task_name>/trace --status recovered
```

요약의 `status`는 launcher가 관찰한 종료 상태이며 과제 성공 판정이 아니다. `judger_score`는 실행 폴더에 공식 `score.json`이 있는 경우에만 복사한다. `wall_clock_s`는 launcher의 실행 시작부터 종료 처리까지이고, 단계별 `duration_sums`는 병렬·중첩 구간을 더하므로 wall-clock과 구분한다. 중단된 마지막 JSONL 줄은 `invalid_lines`로 표시한다.

## 계측 범위

| 구간 | 주요 이벤트·식별자 | 읽을 때의 한계 |
| --- | --- | --- |
| 실행·환경 | `run.start/end`, `environment.launch`, `score.read` | 환경 설정 중 코드가 알 수 없는 월드·난이도·스폰 등은 manifest의 `unrecorded_conditions`에 남긴다. |
| TD | `plan`, `replan`, `graph.created`와 노드·간선 수 | 계획 결과 전체는 기존 TM 이력과 그래프 파일을 참조한다. |
| AC | `task.ready`, `assignment.select`, `task.assigned`, `task.status` | `task.ready`는 코드에서 후보의 가용성까지 충족한 시점이며 순수 DAG 선행조건 충족 시각과 다를 수 있다. 직접/LLM 배정은 `assignment_mode`로 구분한다. |
| SM | 환경 질의와 상태 초기화·갱신 | 해당 span 안의 Gemini 호출을 SM으로 기록한다. 기존 `timed_cache`가 반환한 질의는 내부 span을 거치지 않을 수 있다. |
| BA | `task.execute`, `reflection`, `action.selected`, `action.execute` | 행동 실행 시간과 LLM 호출 시간은 별도다. action ID는 actor 결정 묶음 ID의 하위 call ID다. |
| Gemini·Ollama | `llm.request.start/end`, `llm.cache_hit` | 토큰·finish reason은 공급자가 반환한 경우에만 기록한다. Gemini 비용은 코드 가격표의 추정치이며, Ollama는 `unpriced_requests`로 표시한다. Gemini SDK 내부 재시도는 개별 요청으로 분리되지 않을 수 있다. |

`task_id`·`agent_id`·actor 결정 묶음의 `decision_id`와 요청 ID를 가능한 범위에서 기록한다. 여러 worker에 복사된 task는 `task.child_created`의 원본 ID로 연결한다. actor 내의 LLM 요청과 도구 이벤트는 같은 결정 묶음에 속하지만, 한 LLM 요청을 특정 도구 호출과 1:1로 확정하지 않는다. Controller의 graph 준비·실행 대기나 model server 내부 GPU 추론 시간을 완전히 분해한 trace는 아직 아니다.

기본 trace는 필드 허용 목록을 사용하며 프롬프트·API 키·도구 인자·모델 응답 전문을 수집하지 않는다. 기존 actor 이력·원본 로그는 이와 별개이므로 공유할 때 내용을 확인한다. 모델이 제공하지 않은 내부 추론은 기록할 수 없다. Gemini·Ollama 외의 모델 어댑터와 다른 실행 진입점은 아직 자동 연결하지 않았다.

## 검증

```bash
PYTHONPATH=. .venv/bin/python verification/tracer_checks.py
```

오프라인 fixture는 다중 프로세스 기록, 미완성 줄 복구, 민감 필드 제외, 모의 Gemini 호출·actor callback과 도구 검증을 확인한다. 실제 Minecraft·외부 API를 사용하는 기준선 실행과 trace 완전성 검증은 별도 단계다.
