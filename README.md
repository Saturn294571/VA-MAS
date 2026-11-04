# VA-MAS

VillagerAgent(VA)의 생성형 계획을 유지하면서 **BA 행동 선택과 AC 작업 배정을 결정형 정책으로 분리했을 때 성능·시간·추론 비용이 어떻게 달라지는지** 연구합니다. BA 단일 축을 먼저 검증하고 AC는 실제 선택 기회를 확인한 뒤 비교합니다. 계획·배정·상태·actor·환경 judger의 책임과 증거를 구분합니다.

[연구 안내](doc/research/README.md) · [핵심/보존 기능 경계](doc/core_separation.md) · [과거 이상점 귀속](doc/historical_anomalies_2026-11-04.md) · [실제 환경 smoke](doc/live_smoke_2026-11-04.md)

## 핵심 구성

| 계층 | 구현·역할 |
| --- | --- |
| 계획·상태 | TaskManager, DataManager, Task·Graph와 TD/SM trace |
| 배정 | Full Controller, AssignmentPolicy 계약·검증, 직접/LLM 배정 구분 |
| 행동 | BaseAgent, 공통 ActionPolicy 계약, 생성형 ReAct·Tev1·hybrid·반복 배치 |
| 생성형 모델 | Gemini 또는 명시적 로컬 Ollama; TD·SM·AC·BA 역할별 설정 |
| 환경·평가 | Minecraft 1.19.2, Mineflayer/Flask, Construction·Farming·Escape judger |
| 검증 | TD/AC 프로브와 네트워크 차단 오프라인 fixture |

`archive/full-features-20261104`는 전체 기능 보존 브랜치입니다. RL, 자동 과제 생성·감시, Meta 시나리오, Tiny Controller, FastAPI 대안 서버, 추가 공급자, 과거 검색·학습 자료 가공 도구는 그 브랜치에서 확인합니다. 핵심 실행은 보존 브랜치의 파일이나 과거 프로젝트 폴더를 참조하지 않습니다.

`tiny_start.py`는 **Full Controller를 사용하는 최소 예제**입니다. 별도 Tiny Controller와 다릅니다. 핵심 실행기의 `controller_mode`는 생략하면 `full`이고, `tiny` 등 제거된 값은 명시적으로 거부합니다.

## 설치

Python 3.10과 Node.js 22 이상을 사용합니다. 새 환경은 Miniforge/mamba로 준비할 수 있습니다.

```bash
git clone https://github.com/Saturn294571/VA-MAS.git
cd VA-MAS
mamba create -p ./.venv python=3.10 pip
mamba activate ./.venv
python -m pip install -r requirements.txt
npm ci
```

기본 실행·Ollama·프로브에는 `requirements/base.txt`, Construction의 캐시되지 않은 구조 설명 생성에는 추가로 `requirements/construction.txt`가 필요합니다. 루트 목록은 둘을 포함합니다. 이 설치 목록을 새 환경에 설치하는 작업과 기존의 전체 환경을 복제해 사용한 smoke는 서로 다른 검증입니다. 현재 `.venv`에는 과거 선택 패키지가 남아 있을 수 있으며, 의존성 분리 검사는 해당 SDK의 import를 차단해 수행합니다.

Minecraft 서버·Ollama 서비스·모델 가중치·인증은 저장소에 포함하지 않습니다. Gemini 키는 `GEMINI_API_KEY` 또는 `GOOGLE_API_KEY` 환경 변수로 제공합니다. Ollama가 선택된 역할은 로컬 HTTP만 허용하고 외부 공급자로 자동 대체하지 않습니다. Gemini 어댑터는 Google의 OpenAI 호환 endpoint를 사용하므로 Python `openai` 패키지는 핵심 의존성입니다.

## 실행

세 benchmark의 설정 예시는 `examples/construction_task0.json`, `examples/farming_task0.json`, `examples/escape_task0.json`입니다. 각 실행 전에 고유한 `task_name`과 서버 주소를 정하고, 기존 로그·월드·원시 결과를 보존하세요. 설정 예시는 실제 실행·완료를 보장하는 점수 기록이 아닙니다.

```bash
export VILLAGER_LLM_MODEL=gemini-3.1-flash-lite
export VILLAGER_LLM_THINKING_LEVEL=minimal
mkdir -p .cache
export VILLAGER_BENCH_CONFIG_PATH=examples/construction_task0.json
python start_with_config.py
```

Gemini 3.8 Flash의 기존 기본값은 유지합니다. 역할별 공급자는 `model_roles`로 지정하며 예시는 [Ollama 역할 설정](doc/research/doc/architecture_understand/ollama_roles.md)에 있습니다. 생성형/결정형 BA 선택은 `decision_policies`에 명시합니다. AC `decision`은 아직 미구현이므로 실행기가 거부하며 생성형으로 대신 실행하지 않습니다. Controller 주도 배정 정책은 현재 동질 Construction으로 제한됩니다. Farming·Escape는 예시처럼 `assignment_policy=decomposer`를 사용합니다.

```bash
export VILLAGER_TASK_NAME=tiny_new_unique_run
python tiny_start.py
python -B verification/run_offline.py
python -B td_ac_probe.py --self-test --output /tmp/va-probe-new-run
```

Tiny의 기본 목표는 `Alice talk with yubo`입니다. 대화 대상이 필요하며 하위 작업 1회 성공/실패로 종료하므로 프로세스 종료 코드만으로 상위 목표 성공을 판정하지 않습니다. TD/AC self-test는 합성 상태와 fixture를 사용하며 Minecraft 완주·judger 점수의 대체 검사가 아닙니다.

## 결과와 알려진 한계

실행별 score·action log·manifest·trace는 `result/<task_name>/`에 보존합니다. benchmark 입력과 기존 결과는 변경하지 않았으며 코드·모델·프롬프트·월드가 바뀐 실행을 같은 조건의 반복으로 합치지 않습니다. 과거 기록은 [연구 리포트](doc/research/doc/human_report/report_log.md)에 남깁니다.

모델의 빈 `MALFORMED_FUNCTION_CALL` 응답, 길이 제한, 완료 시 미종료 요청, Tiny의 조기 종료 및 정상 exit code 문제는 [귀속 보고서](doc/historical_anomalies_2026-11-04.md)에 기록했습니다. 이번 기능 분리는 이 동작을 수정하지 않습니다. 원본 기능은 보존 브랜치에 있고 실제로 검증하지 않은 기능까지 정상 실행을 보증하지 않습니다.

## 원본 연구

본 저장소는 [VillagerAgent 공개 코드](https://github.com/cnsdqd-dyb/VillagerAgent)에 기반합니다. 논문–코드 대응은 [구조 지도](doc/research/doc/architecture_understand/VA_code_paper_map.md)를 참고하세요. 원본 소개·설치·Docker 안내는 전체 기능 보존 브랜치에 남겨 두었습니다.

```bibtex
@inproceedings{dong2024villageragent,
  title={VillagerAgent: A Graph-Based Multi-Agent Framework for Coordinating Complex Task Dependencies in Minecraft},
  author={Dong, Yubo and Zhu, Xukun and Pan, Zhengzhe and Zhu, Linchao and Yang, Yi},
  booktitle={Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics},
  year={2024}
}
```
