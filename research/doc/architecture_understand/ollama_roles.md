# TD·SM·AC·BA 생성형 모델 선택

현재 생성형 기준선은 TD·SM·AC·BA 모두 Gemini 외부 API다. 로컬 Ollama 경로는 비교 실험을 위해 명시적으로 선택할 수 있다. 결정형 정책은 별도 단계다.

## 설정

현재 로컬 `base_agent_multi_test_config.json`은 `model_roles.default.provider=gemini`다. 해당 파일은 Git 제외 대상이며 기존 `task_name`이 보존된 결과와 같으면 launcher는 실행을 건너뛴다. `model_roles`를 생략해도 Gemini 경로를 사용한다. 기존 최상위 `api_model`은 역할 선택 설정이 아니며, 실제 적용 모델은 `model_roles`와 실행 `manifest.json`에서 확인한다.

로컬 모델을 다시 비교할 때의 전체 설정은 [Task6·3인 Ollama 예시](../../../examples/ollama_construction_task6.json)를 참고한다. 이 예시는 **명시적 로컬 선택**이다. 예시의 `task_name`은 매 실행마다 변경해야 한다. 실제 실행은 Minecraft 월드와 기존 상태 파일을 바꾸므로 실행 전 결과 보존과 서버 조건을 확인한다.

```json
"controller_mode": "full",
"assignment_policy": "controller",
"model_roles": {
  "default": {"provider": "ollama", "model": "qwen3.8:27b"}
}
```

- `default=ollama`는 TD, SM, AC, BA 전부에 적용되며 Gemini 키가 필요하지 않다. `td`, `sm`, `ac`, `ba` 항목을 별도로 적으면 해당 역할의 default를 덮어쓴다. `default` 자체를 생략하면 지정하지 않은 역할은 기존 Gemini 경로다. Gemini가 하나라도 선택되면 `GEMINI_API_KEY` 또는 `GOOGLE_API_KEY`가 필요하다.
- TD 설정은 task 생성·재계획, SM 설정은 환경·이력 요약, BA 설정은 Minecraft actor 행동 선택 **및 BaseAgent reflection**, AC 설정은 Controller 생성형 배정과 협업 작업 분해에 적용된다. 기존 RL 모드는 별도 경로다.
- Ollama 설정에 `base_url`(기본 `http://127.0.0.1:11434`), `num_ctx`(선택), `timeout`(초, 기본 300)을 지정할 수 있다. 로컬 HTTP 주소만 허용한다. `num_ctx`를 생략하면 Ollama 서버 설정을 사용한다.
- AC 모델 선택은 **full Controller**에서 사용한다. tiny Controller는 직접 배정만 하므로 설정된 AC 모델을 호출하지 않고 이를 시작 시 알린다. full Controller도 후보 수가 필요 인원과 같으면 직접 배정하므로 로컬 AC가 호출되지 않을 수 있다. 현 `assignment_policy=controller` 실행 경로는 Construction·동질 agent로 제한된다.
- 로컬 호출이 실패하면 오류를 기록하고 전파하며 Gemini로 자동 전환하지 않는다. 새 실행의 `task_name`을 고유하게 지정해 기존 결과와 분리한다.
- 전체 역할이 로컬이면 TaskManager의 선택적 Google embedding 경로는 차단된다. 현재 일반 경로의 retrieval은 문서 경로 탐색을 사용하며, 의미 기반 검색을 호출하면 외부로 대체 호출하지 않고 명시적으로 실패한다. Qwen 생성 모델을 embedding 모델로 취급하지 않는다.
- Construction judger가 저장된 blueprint 설명을 찾지 못해 설명을 생성할 때는 별도 judger 프로세스에서 실행된다. 전체 로컬 실행에서는 TD의 Ollama 설정을, 기본 Gemini 실행에서는 Gemini를 사용한다.
- `tiny_start.py`, `agent_demo.py`, `auto_gen_gpt_task.py`, `config.py`의 독립 생성형 호출도 기본적으로 Gemini를 쓴다. 이 경로에서 로컬을 선택하려면 `VILLAGER_GENERATION_PROVIDER=ollama`를 설정한다. `start_with_config.py`의 역할별 선택은 그 변수 대신 각 실행의 `model_roles`를 따른다.

## API와 측정

Ollama native `/api/chat`에 `think: false`를 명시한다. 이 서버에서 OpenAI 호환 endpoint에 같은 설정을 전달한 단문 테스트는 출력 없이 길이 제한에 도달했지만, native endpoint는 응답했다. 따라서 두 경로를 동일하게 취급하지 않는다. Ollama 도구 호출은 기존 LangChain structured ReAct 및 BA 행동 검증기를 거친다.

Local adapter는 `prompt_eval_count`, `eval_count`, `done_reason`과 load/prompt-eval/eval 시간을 trace에 기록한다. `data/tokens.json`에는 `ollama/<model>` 항목을 추가한다. 로컬 실행의 금전적 비용은 추정하지 않으며 summary의 `unpriced_requests`에 표시한다. 총 `cost_usd`는 가격이 기록된 외부 요청의 추정 합계다. Ollama의 control-plane 캐시는 모델 객체 수명 동안의 메모리 캐시이며 Gemini의 기존 파일 캐시와 같지 않다. 모델·배포 방식·캐시 차이를 실험 조건에 포함해야 한다.

Ollama 호출은 `localhost` HTTP를 거치므로 로컬 통신·서버 대기·모델 로딩·GPU 경합은 남는다. 시스템 프록시 설정은 Ollama 호출에 적용하지 않는다. 외부 API 네트워크 지연은 전체 로컬 설정에서 제외된다. 작은 오프라인 fixture는 `PYTHONPATH=. .venv/bin/python verification/ollama_model_checks.py`로 실행한다. 이것은 Minecraft benchmark 완주나 모델 간 성능 비교가 아니다.
