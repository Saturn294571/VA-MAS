# 실제 환경 smoke test — 2026-11-04

요청한 Gemini 3.1 Flash-Lite로 `tiny_start.py`와 Full Controller·Construction Task0를 실제 Minecraft 1.19.2에서 실행했다. Task0는 judger 완료와 독립적인 월드 조회가 일치했고, Tiny는 추가 진단에서 실제 채팅 수신까지 확인했다. 종료 코드와 상위 과제 성공은 구별한다.

## 조건과 재현 근거

- 코드 기준: `60f6afb`; 아래 모델 지원·환경 설정 변경이 적용된 dirty tree에서 실행했다. 사용자가 진행 중인 `research/` → `doc/research/` 이동은 수정하지 않았다.
- 모델: `gemini-3.1-flash-lite`, `thinking_level=minimal`, actor 출력 상한 1024. TD·SM·AC·BA 공급자는 Gemini로 설정했다. 임베딩 기본값은 변경하지 않았다.
- Minecraft: Vanilla 1.19.2, Java 17.0.20.1, 새 flat/Peaceful/Survival 월드, localhost:25565, benchmark용 offline 인증. 기존 서버·월드는 실행하거나 초기화하지 않았다.
- Full: Task0, 1인 Alice, `controller_mode=full`, `assignment_policy=controller`, BA/AC `generative`, `dig_needed=false`. Task0는 desert lamp 3블록 과제다.
- Tiny: 기본 `Alice talk with yubo`, 1인 Alice, 기존 성공/실패 1회 종료 조건. 실제 Mineflayer 관찰 bot yubo를 대화 대상으로 사용했다.
- 조건별 단일 smoke/진단이며 모델·서버 위치 조건이 다른 실행을 같은 조건의 반복 비교로 합치지 않는다.

- 환경·코드 해시·설치 목록·전체 비교: [live_smoke_20261104_031004](..//home/pluto2479/Documents/VA-MAS/result/live_smoke_20261104_031004/environment.json), [비교 JSON](..//home/pluto2479/Documents/VA-MAS/result/live_smoke_20261104_031004/run_comparison.json), [서버 로그](..//home/pluto2479/Documents/VA-MAS/result/live_smoke_20261104_031004/minecraft-server.log).
- 정확한 모델 ID와 표준 텍스트 가격은 [공식 모델 문서](https://ai.google.dev/gemini-api/docs/models/gemini-3.1-flash-lite)와 [공식 가격표](https://ai.google.dev/gemini-api/docs/pricing#gemini-3.1-flash-lite)를 2026-11-04에 확인했다. 입력 $0.25/백만 token, 출력 $1.50/백만 token으로 기록한다.

## 실행 결과

| 실행 | 프로세스 시간 | 응답 기록 | 추정 비용 | 판정 |
| --- | ---: | ---: | ---: | --- |
| [Tiny 기본 진단](../result/gemini31lite_tiny_smoke_20261104_031004_retry1/smoke_execution.json) | 31.47s | 8 | $0.00639775 | 이동·탐색 확인. 첫 하위 작업 성공 후 종료하여 대화는 미실행 |
| [Tiny 가까운 대상, 첫 진단](../result/gemini31lite_tiny_smoke_20261104_031004_retry1_nearby/smoke_execution.json) | 15.99s | 6 | $0.00295725 | 빈 MALFORMED_FUNCTION_CALL, 행동 0회·reflection 실패. 종료 코드는 0 |
| [Tiny 가까운 대상, 재시도](../result/gemini31lite_tiny_smoke_20261104_031004_retry1_nearby_retry1/smoke_execution.json) | 20.25s | 8 | $0.00565300 | navigateTo·talkTo 성공, 서버 채팅 및 관찰 bot 수신 확인 |
| [Full Construction Task0](../result/gemini31lite_full_task0_1p_smoke_20261104_031004/smoke_execution.json) | 46.34s | 14 | $0.01250725 | 3/3 블록, BHR/VHR=1.0, complete task, 독립 월드 조회 일치 |

모든 실제 실행은 종료 코드 0이다. 별도로 mamba 옵션 오류로 프로세스 시작 전 종료 코드 2였던 setup 시도도 원래 결과 폴더에 보존했다. API 사전 연결 확인 1회는 5 input + 2 output token으로 정상 응답했다.

- Full 원시 근거: [judger score](../result/gemini31lite_full_task0_1p_smoke_20261104_031004/score.json), [독립 blockAt 조회](../result/gemini31lite_full_task0_1p_smoke_20261104_031004/world_verification.json), [console](../result/gemini31lite_full_task0_1p_smoke_20261104_031004/console.log), [trace summary](../result/gemini31lite_full_task0_1p_smoke_20261104_031004/summary.json).
- Tiny 대화 근거: [서버 채팅 수신](../result/gemini31lite_tiny_smoke_20261104_031004_retry1_nearby_retry1/server_chat_evidence.json), [행동 로그](../result/gemini31lite_tiny_smoke_20261104_031004_retry1_nearby_retry1/runtime_snapshot/action_log.json), [trace summary](../result/gemini31lite_tiny_smoke_20261104_031004_retry1_nearby_retry1/summary.json).

## 확인한 이상점과 한계

1. **모델의 빈 도구 응답:** Full에서 한 번, 가까운 대상 Tiny 첫 진단에서 한 번 `function_call_filter: MALFORMED_FUNCTION_CALL`이 관찰됐다. 실제 행동 없이 LangChain chain이 끝날 수 있다. Tiny 실패도 process exit 0이므로 종료 코드만을 과제 성공으로 사용하면 안 된다. 모델·프롬프트·파서의 광범위한 변경이나 자동 fallback은 하지 않았다.
2. **Tiny 종료 조건:** 기본 `stop_after_success_times=1`은 상위 대화 목표가 아니라 하위 작업 성공을 센다. 첫 진단은 yubo 탐색 성공 뒤 종료했다. 대상 위치를 가까이 한 별도 진단과 그 재시도를 구분해 보존했다. 마지막에는 인사 메시지 전달까지 확인했으나, 여러 차례 대화나 사람 응답까지 완료한 benchmark 점수는 없다.
3. **잘린 상태 요약:** Full의 SM 응답 한 번이 `finish_reason=length`였다. 이번 3블록 완료를 막지는 않았지만 복잡한 과제에서 정보 손실 여부는 후속 검증 대상이다.
4. **완료 시 진행 중인 API 요청:** Full trace는 LLM start 15개, end 14개다. judger 완료로 launcher가 child를 종료할 당시 마지막 actor 요청이 진행 중이었다. 기록된 비용은 실제 청구액 전체를 보장하지 않는다.
5. **AC 모델 선택 미관찰:** Full Controller를 사용했지만 1인 Task0의 배정은 모두 direct 3회였다. TD·SM·BA의 실제 호출과 Full의 배정 검증 경로는 확인했으며 AC LLM의 여러 후보 선택은 이번 smoke 범위에서 확인하지 못했다.
6. **judger efficiency 해석:** score의 `efficiency=101.3401`, `use_time=3.0`은 기존 행동 시간 기준 계산이다. 총 시간 약 46초와 다르며, 이를 101% 완료율이나 agent 증가 효과로 해석하지 않는다.
7. **비용 추정:** 네 실행에서 응답 기록 36개, 비용 약 $0.02751525다. 사전 호출을 더하면 약 $0.02751950이지만 진행 중 중단 요청·서비스 청구 정책은 별도다. 총 비용과 과제 성공을 혼용하지 않는다.

## 새 경로의 셋업 처리

- Miniforge 도구로 기존 Python 3.10.20 환경의 파일을 재배치하여 프로젝트 `.venv`를 만들고 `mamba run -p .../.venv`로 검증·실행했다. 일반 `conda create --clone --offline`은 과거 package cache가 없어 실패했다. 이후 conda-pack tar 방식으로 복구했고 prefix·모듈 위치·실제 API 동작을 확인했다. 원본 환경은 변경하지 않았다.
- `.venv`는 기존 패키지를 보존한 약 6.5GB 환경이다. 기능별 requirements로부터 최소 설치한 환경의 재현 검증은 아니다. Conda 캐시 누락 경고가 있었고, `mamba run`의 실제 prefix와 라이브러리 import로 동작 여부를 검증했다.
- `npm install`로 246개 패키지를 설치하고 `package-lock.json`을 생성했다. 현재 Mineflayer 4.39.0과 minecraft-protocol은 Node >=22를 요구해 기존 Node 20 대신 프로젝트 내부 `.runtime/node`에 Node 22.23.4를 설치했다. `package.json`에도 요구 버전을 명시했다.
- 로컬 `.venv/etc/conda/activate.d/va-mas-node.sh`가 프로젝트 Node 22를 PATH에 추가한다. `mamba run -p .venv node --version`에서 v22.23.4를 확인했다. sandbox에서는 mamba proc cache를 프로젝트 `.cache`로 지정했다.
- 모델 어댑터에 3.1 Flash-Lite allowlist·가격·가격 확인일을 추가했다. 3.8 기본값은 유지하고 이번 실행에서만 환경 변수로 모델을 선택했다.
- Tiny에는 `MINECRAFT_HOST`, `MINECRAFT_PORT`, `VILLAGER_TASK_NAME` 환경 override를 추가해 기본 동작을 유지하면서 실행별 산출물 충돌을 피했다.
- 복제 실패본과 중간 tar 약 13GB는 정상 환경 검증 후 제거했다. 새 `.venv`, Node 의존성, 테스트 월드와 원시 결과는 남겼다.
- 키 값은 코드·문서·로그에 저장하지 않았고, 사용자 제공 임시 비공개 파일에서 메모리로 읽어 실행했다. 서버 설정의 별도 RCON 인증은 ignored runtime 안에만 둔다.

## 재실행과 종료 상태

로컬 터미널에서 기존 키를 환경 변수로 준비한 뒤 다음처럼 실행할 수 있다. 서버는 테스트 종료 후 모든 dimension을 저장하고 정지했다. 다시 실행하려면 준비한 테스트 서버를 명시적으로 시작해야 한다. 기존 월드를 초기화하지 말고 새로운 task_name을 사용한다.

```bash
mamba activate ./.venv
export VILLAGER_LLM_MODEL=gemini-3.1-flash-lite
export VILLAGER_LLM_THINKING_LEVEL=minimal
export VILLAGER_GENERATION_PROVIDER=gemini
export VILLAGER_BA_POLICY=generative
export VILLAGER_TASK_NAME=tiny_smoke_new_unique_name
python tiny_start.py
```

Full은 보존된 `construction_task0_config.json`을 복사해 `task_name`을 새 값으로 바꾸고 `VILLAGER_BENCH_CONFIG_PATH`로 지정한다. `.cache`가 없는 새 실행에서는 먼저 생성해야 한다. 기존 결과 폴더는 launcher가 덮어쓰지 않고 건너뛴다.

새 환경에서 오프라인 runner도 실행했다. [8개 검사 항목](..//home/pluto2479/Documents/VA-MAS/result/live_smoke_20261104_031004/offline_validation.json)이 모두 통과했으며 unittest 37개·행동 assertion 스크립트 2개·TD/AC self-test를 포함한다. 실제 서버 로그·trace·점수·행동 로그는 run별로 보존했다.
