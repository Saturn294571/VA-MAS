# MineSkynet 프로젝트 작업 보고 로그

> 문서 역할: 구현 과정에서 이미 보고한 내용과 당시의 완료·미완료 판단을 시간순으로 누적한다. 과거 보고는 후속 결과로 덮어쓰거나 삭제하지 않고, 새 검증 결과는 별도 보고 항목으로 추가한다. 목표와 다음 순서는 마일스톤에서 관리하고, 교수님께 제시할 내용은 `labmeeting_temp.md`에서 선별·편집한다. 각 단위 테스크당 보고 템플릿/예시는 아래와 같다. 불렛포인트(-)/번호 목록(1))/체크포인트([X])/표(|---|---|---|) 등은 이해를 돕기 위해 적절히 사용한다. 반드시 /home/pluto2479/Documents/MineSkynet/research/AGENTS.md 의 원칙을 준수하라.

```markdown
# MineSkynet 프로젝트 작업 보고 로그

## YYYY-MM-DD — 단위 테스크 제목 1

...

### n. 하위 테스크 이름

...

#### n.m. 하위 테스크의 세부사항 (논리상/분량상 구분할 필요가 있을경우)

...

## YYYY-MM-DD — 단위 테스크 제목 2

...

```

## 2026-08-19~20 — Odyssey 환경·의존성 진단과 현대화 범위 확정

작성일: 2026-08-19~20  
대상 코드: 공개 Odyssey와 당시 `experiment/mvp-core` 진단 환경

### 1. 논문상 기능과 진단 목적

Odyssey는 Minecraft environment에서 open-world skill library, semantic skill retrieval과 planner–actor–critic을 연결한다. 당시 가장 먼저 해결해야 할 문제는 model 성능이 아니라 Minecraft server → Mineflayer → JavaScript skill → state-based verification으로 이어지는 실행 고리를 안정화하는 것이었다.

원본 공개 코드는 작은 행동을 실행할 때에도 planner, critic, embedding model, Chroma, launcher와 model provider를 함께 초기화했다. 이 결합 때문에 오류가 어느 논문 기능에서 발생했는지 구분하기 어렵고, 사용하지 않는 legacy dependency까지 모든 환경에 설치해야 했다.

문제를 분리하기 위해 E0~E4 gate를 임시 진단 도구로 사용했다. 이 gate는 결함 격리 과정의 역사적 이름이며, 이후 MineSkynet 연구 개발 순서나 최종 연구 기여로 사용하지 않는다.

### 2. 진단에서 확정한 원칙

#### 2.1 논문 기능과 실행환경의 분리

Planner–actor–critic, semantic retrieval과 skill library는 보존해야 할 Odyssey의 논문 기능이다. 반면 Multiplayer Server Pause bundle, launcher와 특정 model provider SDK는 특정 실행 방식에 필요한 dependency이므로 profile로 격리할 수 있다.

따라서 기본 profile에서 비활성화하는 것과 연구 시스템에서 기능을 제거하는 것을 구분한다.

#### 2.2 현대화의 연구 범위 제한

Odyssey 현대화의 목적은 legacy보다 빠르거나 우수함을 증명하는 것이 아니라, 구형 dependency issue로부터 안전한 MineSkynet 실험 기반을 만드는 것이다. `master`는 논문 기능과 공개 구현을 확인하는 source reference로 사용하며 legacy runtime의 성공률·latency 재측정은 완료 조건으로 삼지 않는다.

#### 2.3 신뢰받는 외부 구현의 보존

Sentence Transformer, Chroma와 LangChain은 semantic retrieval의 서로 다른 기능을 담당한다. 구형 API와 지원 조합은 갱신할 수 있지만, 이들을 근거 없이 자체 구현으로 교체하지 않는다. 변경 전후에 동일 corpus의 index 생성·재로드와 candidate retrieval contract를 먼저 보존한다.

#### 2.4 Model 성공과 embodied agent 성공의 구분

Minecraft 질문에 답하거나 training loss가 감소하는 것은 Actor가 올바른 skill을 선택해 environment state를 바꿨다는 증거가 아니다. Model 평가는 candidate-valid selection과 실제 Minecraft state delta까지 연결해야 한다.

### 3. 교수 피드백과 현재 해석

| 과거 피드백 | 현대화에 남긴 원칙 |
| --- | --- |
| 환경 설정이 최우선 | model·분산 연구 전에 반복 가능한 executor와 state verification을 확보한다. |
| 최소 dependency만 유지 | 기능을 삭제하지 않고 executor, retrieval, model, launcher, combat와 training profile을 분리한다. |
| 작은 model의 성능이 부족할 수 있음 | local model은 자유 계획·code generation보다 bounded skill selector부터 평가한다. |
| LoRA의 의미가 약하면 중단 | zero-shot/base model과 동일 task에서 비교하고 online 성공 개선이 없으면 학습을 연구 핵심에서 제외한다. |
| 새 기억이 기존 능력을 훼손할 수 있음 | 기본 MineSkynet Actor는 read-only registry를 사용하고 능동 skill lifecycle은 별도 Voyager/Full profile에서 검증한다. |
| 복잡한 문제를 더 복잡하게 만들지 말 것 | 한 고리씩 격리하되 component smoke를 전체 시스템 완료로 표기하지 않는다. |

### 4. E0 실행 계층에서 먼저 확인한 결과

Model 없이도 기존 Odyssey skill이 modernized Mineflayer 환경에서 반복 실행되고, failure 뒤 bridge가 다시 요청을 받을 수 있는지 확인했다.

- Minecraft `1.19.4`, Java `17`, Node `20.13.1` 조합 고정
- Mineflayer `4.25.0`과 관련 Prismarine dependency를 lockfile에 고정
- `/pause` 없는 mod-free server에서 raw 원목 채집과 작업대 제작을 각각 10/10 통과
- chat message가 아니라 inventory delta로 success 판정
- 잘못된 연결, 연속 reset과 의도적 skill error 뒤 bridge recovery 확인
- 실행 계층 결과를 commit `a157205`와 tag `odyssey-modernized-executor-1.19.4`로 고정

이 결과는 Minecraft execution layer의 범위이며 Odyssey 전체 논문 환경 재현을 뜻하지 않는다. 환경 snapshot과 반복 결과는 바로 다음 E0 증거 보고에 상세히 기록한다.

### 5. 실행 계층에서 분리·해결한 결합

| 문제 | 연구자가 이해할 한 줄 의미 | 처리 |
| --- | --- | --- |
| Multiplayer Server Pause bundle | model 응답을 기다리는 동안 world를 멈추는 legacy 장치이며 raw skill 실행에는 필요하지 않음 | modernized executor 기본 경로에서 제외하고 Python legacy adapter에만 남김 |
| global bot lifecycle | 이전 bot의 늦은 종료가 새 bot까지 종료해 서로 다른 request의 상태가 섞임 | request-local bot과 identity check 적용 |
| non-finite motion | chunk 준비 전 physics가 잘못된 position packet을 보낼 수 있음 | chunk readiness와 finite-state guard 적용 |
| offline operator UUID | 새 world에서 bot이 reset command 권한을 얻지 못함 | 재현 가능한 offline UUID profile 고정 |
| mutable Node dependency tree | 설치 시점마다 protocol·physics dependency 조합이 달라질 수 있음 | exact package-lock과 health/version response 고정 |

### 6. E0 이후 다시 연결할 논문 기능

다음 기능은 E0에서 제거한 것이 아니라 modernized Odyssey에 다시 연결해야 할 범위로 남겼다.

- 40 primitive + 183 compositional skill corpus
- Sentence Transformer 기반 description/query embedding
- top-5 기본·top-10 별도 profile의 semantic retrieval
- MineMA Actor의 exact candidate selection
- recursive prerequisite execution
- planner–actor–critic feedback과 replanning
- 논문 benchmark의 task·prompt·success condition

Voyager의 curriculum, code generation/repair와 dynamic skill commit도 삭제하지 않는다. 공개 Odyssey의 fixed-library baseline과 분리해 `voyager-lifelong`과 `odyssey-full` profile에서 보존한다.

### 7. 당시 상태와 해석

E0~E4 gate는 dependency 결함을 격리하는 데 유용했지만, 각 gate의 최소 통과를 연구 목표로 확대해서는 안 된다고 판단했다. 이후에는 “원본 논문 기능을 재현하되 불안정하거나 비효율적인 dependency 고리를 제거·대체·업데이트한다”는 방향으로 마일스톤을 재편했다.

### 8. 근거 파일

- [원본 환경·의존성 진단 문서](MVP_report.md)
- [E0 원시 증거](E0_test_evidence_2026-08-20.md)
- [현대화 마일스톤](milestone_goal/modernization_milestone.md)
- [논문–코드–dependency 대응표](paper_code_dependency_map.md)

## 2026-08-20 — E0 Minecraft execution layer 검사 증거

작성일: 2026-08-20  
검사 profile: `e0-executor` 후보 환경

### 1. 논문상 기능과 증거 범위

이 검사는 model과 Planner를 제외하고, Actor가 선택할 JavaScript skill을 Mineflayer가 실제 Minecraft state change로 실행할 수 있는지 확인했다. 구체적으로 raw Odyssey skill의 반복 실행, inventory delta 기반 success 판정과 failure 이후 bridge recovery를 검증했다.

이는 Odyssey의 Minecraft execution layer에 대한 증거이며 semantic retrieval, MineMA Actor와 planner–actor–critic 전체 재현을 의미하지 않는다. 원시 world와 cache는 Git 밖의 `Odyssey/runtime/`에 유지했다.

### 2. 환경 snapshot

- Git 기준 commit: `80a42fcbd2b5da53ecf7e58f1036981e428c9590` (`origin/experiment/mvp-core`); 검사 시점에는 E0 관련 uncommitted change가 존재
- Docker image: `itzg/minecraft-server:java17`
- image ID: `sha256:5b3e96bcd7dace8ab7be89c245dc9ba0b1573fdef2f01d3e101ac40e7843fa70`
- Minecraft `1.19.4`, Fabric Loader `0.15.11`, Java `17.0.15+6`
- world seed: `7634567288700934061`
- Node `20.13.1`, npm `10.5.2`
- offline-mode bot operator UUID: `67128b5b-2e6b-3ad1-baa0-1b937b03e5c5` (`OfflinePlayer:bot`)
- operator profile: `Odyssey/server-profile/e0/ops.json`
- `package-lock.json` SHA-256: `5555e896e0c5d19c635965bc9338b0cd60a248092bc9c8ff65a6c678943a6b7c`

직접 Node dependency는 다음 조합으로 고정했다.

| Dependency | Version |
| --- | ---: |
| mineflayer | 4.25.0 |
| minecraft-data | 3.83.0 |
| mineflayer-pathfinder | 2.4.2 |
| mineflayer-tool | 1.2.0 |
| local mineflayer-collectblock | 1.4.1 |
| express | 4.18.2 |
| vec3 | 0.1.8 |
| typescript | 4.9.5 |
| @types/node | 18.19.130 |
| prismarine-entity | 2.4.0 |
| prismarine-item | 1.15.0 |

`npm ci` 감사에서는 16 vulnerabilities(3 low, 6 moderate, 7 high)가 보고됐다. 호환성이 검증된 묶음을 임의 변경하지 않기 위해 `npm audit fix`는 실행하지 않고 warning과 영향 범위를 후속 관리 대상으로 남겼다.

#### 2.1 기존 optional mod bundle snapshot

| JAR | Version | SHA-256 |
| --- | ---: | --- |
| Multiplayer Server Pause | 1.3.1 | `fe6fe7e5c398415578f2be355de4bcd74ed5f11ebb5929d1aa91381fa8074d24` |
| CompleteConfig | 2.3.1 | `f7d5c7c82df363305b726f6fad651a68dad8404322d4b7a0f46d948882affcc2` |
| Fabric API | 0.87.2+1.19.4 | `a92650d48a9f672dc74e8b1eaefedb28dc83a13a80431215900181aa3a8675d8` |
| iChunUtil | 1.0.2 | `661b800c180d8f0dfca2467bebfbd57c41cd6b9e22cac989fb8979e3137d6475` |

이 JAR은 legacy pause fixture의 snapshot이며 mod-free raw executor의 필수 dependency로 판정하지 않았다.

### 3. Dependency와 interface 정적 검사

1. 활성 dependency tree에서 과거 `mineflayer-collectblock/node_modules`를 분리한 뒤 `npm ci`가 성공했다.
2. `npm run check`가 local collectblock TypeScript build, `node --check index.js`, `npm ls --depth=0`을 모두 통과했다. `npm ci` 뒤에도 하위 `mineflayer-collectblock/node_modules`는 생성되지 않았다.
3. `/health`와 `/version`은 pinned Minecraft `1.19.4`와 dependency version을 반환했다.

### 4. Minecraft runtime 반복 결과

#### 4.1 Connection과 finite state

Modded fixture에서 bot 연결과 finite position을 0·5·10·15·20·25·30초에 확인해 7/7 통과했다. Clean `npm ci` 직후에도 30초 연결, 원목 1회와 작업대 1회를 다시 실행해 모두 통과했다.

#### 4.2 Raw skill state delta

매회 hard reset과 empty inventory로 두 raw skill을 각각 10회 실행했다.

| Raw skill | 반복 | Before | After | State-based success | Error |
| --- | ---: | --- | --- | --- | --- |
| `mineWoodLog` | 10/10 | `{}` | `spruce_log: 1` | log delta `+1` | `onError: []` |
| `craftCraftingTable` | 10/10 | `{}` | `crafting_table: 1` | table delta `+1` | `onError: []` |

`Odyssey/scripts/e0_regression.py`로 기존 fixture에서 두 작업을 다시 실행한 최종 회귀도 총 20/20, 모든 목표 delta `+1`, 모든 `onError: []`로 통과했다.

#### 4.3 Mod-free executor

별도 임시 Fabric server는 같은 image ID, Minecraft version, Fabric Loader와 seed를 사용하되 외부 mod JAR를 넣지 않았다. Server log의 mod 목록은 Minecraft, Java, Fabric Loader와 내장 MixinExtras뿐이었다.

이 server에 `soft`로 접속해 finite position 30초, 원목 채집과 empty inventory의 작업대 제작을 각각 통과했다. 실행 경로는 `/health`, `/start`, `/step`만 호출하고 `/pause`를 호출하지 않았다. 따라서 raw E0 execution에는 Multiplayer Server Pause, iChunUtil, CompleteConfig와 Fabric API가 필요하지 않음을 확인했다.

### 5. Failure recovery와 bot lifecycle

`/start`가 request별 bot instance를 capture하도록 수정하고 pending start response와 old-bot disconnect를 분리했다. 다음 recovery fixture를 통과했다.

- 연속 hard `/start` 2회 뒤 새 bot 15초 생존
- 잘못된 port의 400 response 뒤 bridge 생존 및 정상 hard reset recovery
- 의도적인 `/step` JavaScript error 뒤 connection 유지
- request-local process exception listener 정리 뒤 다음 request 수신

새 offline-mode server에서는 `OPS=bot`이 online UUID를 기록해 hard reset timeout을 일으키는 문제를 확인했다. 올바른 offline UUID를 담은 `OPS_FILE`을 Compose에 고정한 뒤 외부 mod 없는 새 server의 첫 번째·두 번째 hard reset, 15초 finite position, 원목과 작업대를 모두 통과했다.

### 6. Latency 관찰값

| Raw skill | 평균 action latency | P95 action latency |
| --- | ---: | ---: |
| `mineWoodLog` | 10,829.307 ms | 20,384.104 ms |
| `craftCraftingTable` | 13,172.842 ms | 23,990.514 ms |

Latency는 modernized가 legacy보다 빠르다는 비교 증거가 아니라, 당시 반복 실행의 환경 관찰값으로만 보존한다.

### 7. 해결한 결함과 증거 위치

- old bot의 늦은 disconnect가 새 global bot을 종료하던 race를 request-local bot capture와 identity check로 해결했다.
- `/step` process-level exception listener가 request-local bot을 사용하고 response `finish`/`close`에서 정리되게 했다.
- 새 offline server의 hard reset timeout 원인을 잘못된 online OP UUID로 식별하고 Compose가 traceable offline UUID `OPS_FILE`을 사용하게 했다.
- 최종 raw 결과는 `Odyssey/odyssey/env/results/e0/20260820T021925+0900/`에 저장했다. `environment.json`, 실행별 JSON 20개, `summary.json`, `minecraft_latest.log`를 포함하며 local runtime 결과라 Git에서 제외된다.
- 검사 당시에는 success commit/tag를 만들지 않았고, 이후 변경을 `a157205` (`E0 finished`)에 commit한 뒤 `odyssey-modernized-executor-1.19.4` annotated tag로 local·remote에 고정했다.

### 8. 당시 상태와 해석

Minecraft execution layer는 clean install, raw action success와 대표 failure recovery를 반복 통과했다. 이 결과로 model·retrieval과 분리된 mod-free executor baseline을 확보했다. 다만 E0는 Odyssey 전체 재현이 아니며, semantic retrieval, Actor selection, recursive prerequisite와 planner–actor–critic은 별도 component 검증으로 남았다.

### 9. 근거 파일

- [원본 E0 검사 증거](E0_test_evidence_2026-08-20.md)
- [E0 regression script](../../../MineSkynet-odyssey/Odyssey/scripts/e0_regression.py)
- [E0 server profile](../../../MineSkynet-odyssey/Odyssey/server-profile/e0/ops.json)
- [환경·dependency 진단 기록](MVP_report.md)
- [현대화 마일스톤](milestone_goal/modernization_milestone.md)

---

## 2026-08-27 — Primitive runtime 결함 정리

작성일: 2026-08-27
대상 브랜치: `experiment/odyssey-modernized`

### 1. 논문상 기능과 작업 범위

Odyssey의 open-world skill library는 40개 primitive skills와 183개 compositional skills로 구성된다. Primitive skills는 Mineflayer JavaScript API 위에서 parameterized input을 받는 foundational interfaces이며, compositional skill이 더 복잡한 task와 prerequisite를 재귀적으로 수행할 때 사용하는 저수준 실행 단위다. 논문은 시각 입력이 없는 환경에서 precise positioning과 orientation을 담당하는 spatial skills가 특히 중요하다고 설명한다.

이번 작업은 Odyssey-added spatial primitive 가운데 `goto`와 `getAnimal`을 대상으로 했다.

- `goto`: 지정 좌표의 허용 오차 안으로 bot을 이동시킨다.
- `getAnimal`: 동물 종류에 맞는 먹이를 들고 해당 동물을 지정 좌표까지 유인한다.

목적은 두 함수를 새 행동으로 대체하는 것이 아니라, compositional skill이 호출했을 때 조용히 성공하거나 무한 대기하지 않고 논문상 primitive contract를 실제 Minecraft state로 확인할 수 있게 하는 것이었다.

### 2. 확인한 결함

| Primitive | 공개 코드 결함 | 논문 기능에 미치는 영향 |
| --- | --- | --- |
| `goto` | `bot.entity.positon` 오타 | 현재 위치를 읽을 수 없어 이동 contract 실행 불가 |
| `goto` | x·y·z 세 축이 모두 오차를 벗어날 때만 반복하는 조건 | 한 축만 멀어도 성공으로 종료할 수 있음 |
| `goto` | timeout과 최종 위치 검증 부재 | pathfinder 정지·부분 이동을 성공과 구분하기 어려움 |
| `getAnimal` | `type = "sheep"` 형태의 대입 조건과 항상 참인 ` | | "cow"` | 입력 animal type과 무관하게 잘못된 먹이 분기로 진입 |
| `getAnimal` | `chichken` 오타와 입력·먹이 검증 부재 | chicken branch와 failure 원인을 신뢰할 수 없음 |
| `getAnimal` | 동물을 찾은 뒤 target으로 bot만 이동 | 동물이 실제 target까지 따라왔는지 확인하지 않음 |

### 3. 수정 내용

`goto`는 finite coordinate와 positive timeout을 검사하고, Mineflayer pathfinder의 `GoalNear`를 사용해 반경 2블록 안으로 이동하게 했다. 이동 전·후 위치를 검사하고 timeout이나 pathfinder failure가 발생하면 goal을 취소한 뒤 `[goto]` 오류로 반환한다.

`GoalNear`는 실수 좌표를 Minecraft block-grid로 내림해 반경을 계산한다. 따라서 초기 구현처럼 실수 target과 bot 중심 사이의 Euclidean distance를 후조건으로 사용하면 pathfinder는 성공했는데 primitive가 실패하는 불일치가 생긴다. 최종 contract는 `GoalNear`와 동일한 block-grid distance 2 이하로 통일했다.

`getAnimal`은 animal–food mapping을 다음과 같이 명시했다.

- sheep·cow → wheat
- chicken → wheat seeds
- pig → carrot

지원하지 않는 animal type, 먹이 부재, 32블록 안에서 animal을 찾지 못한 경우를 명시적 오류로 분리했다. 동물을 찾으면 먼저 접근해 바라보고, 먹이를 든 상태에서 `goto`로 target까지 이동한 뒤 animal이 target 반경 4블록 안에 들어왔는지 최대 100 tick 동안 확인한다.

### 4. Offline fixture 결과

mock bot과 pathfinder를 사용한 state-based fixture 14개가 모두 통과했다.

- `goto` 6개: 이미 반경 안인 경우, 정상 GoalNear 이동, 실제 실패 좌표의 block-grid 회귀, 비정상 좌표, timeout·goal 취소, target 미도달 실패
- `getAnimal` 8개: 네 animal–food mapping, 지원하지 않는 type, 먹이 부재, animal 탐색 실패, target까지 따라오지 않는 경우

```text
14/14 primitive offline fixtures passed
```

### 5. Minecraft online fixture 결과

`getAnimal(cow)`은 bot 근처에 cow 한 마리와 wheat를 준비하고 현재 위치에서 x축 8블록 떨어진 target까지 유인했다. 최종 bot–target 거리는 약 `0.842`, cow–bot 거리는 약 `2.223`이었고 `onError` 없이 통과했다.

`goto` 첫 실행은 6블록 이동 뒤 실수 target 거리 `2.154`에서 primitive 오류를 반환했다. 그러나 이는 pathfinder 이동 실패가 아니라 `GoalNear`의 block-grid 반경과 실수 좌표 후조건의 불일치였다. 실제 관측 좌표를 offline regression fixture에 추가하고 contract를 통일한 뒤 다시 실행했다.

재실행에서는 다음 결과로 통과했다.

```text
bot_distance_to_target: 1.3954
bot_block_distance_to_target: 1.4142
onError: []
PASS: goto state-based online fixture
```

### 6. 당시 상태와 해석

`goto`와 `getAnimal`은 offline 14/14와 실제 Minecraft online fixture를 통과했다. 이는 두 spatial primitive의 contract를 확인한 component 결과이며 primitive 40개 전체 또는 Odyssey end-to-end 재현 완료를 뜻하지 않는다. 나머지 primitive contract와 Voyager-inherited interface fixture는 후속 검증으로 남겼다.

### 7. 근거 파일

- [Primitive 40 working manifest](../manifest/odyssey_primitive_40.json)
- [Offline primitive fixture](../../../MineSkynet-odyssey/Odyssey/scripts/primitive_runtime_offline.js)
- [Online primitive fixture](../../../MineSkynet-odyssey/Odyssey/scripts/primitive_runtime_online.py)
- [실행 절차](../README.md#37-primitive-runtime-online-fixture)
- [현대화 마일스톤](milestone_goal/modernization_milestone.md)

---

## 2026-08-27 — Semantic encoder 조건 고정

작성일: 2026-08-27  
대상 브랜치: `experiment/odyssey-modernized`

### 1. 논문상 기능과 이번 작업의 목적

Odyssey의 LLM Actor는 Planner가 생성한 text-based subgoal을 바로 실행 코드로 바꾸지 않는다. 먼저 subgoal을 **query context**로 encoding하고, open-world skill library에 저장된 **skill description**과의 vector similarity를 계산해 **semantic closeness**가 높은 skill을 retrieval한다. Actor는 이렇게 제시된 top-5 relevant skills 중 subgoal 실행에 가장 적절한 code를 선택한다.

Skill library 쪽에서는 각 skill의 complete program code를 바탕으로 자연어 description을 생성하고, Sentence Transformer가 이 description을 vector representation으로 변환한다. 따라서 semantic encoder는 다음 두 입력을 같은 의미 공간에 배치하는 논문 기능이다.

- Planner가 생성한 자연어 subgoal: retrieval의 query context
- 183개 compositional skill의 자연어 description: 검색 대상 corpus

이번 작업의 목적은 이 논문 기능을 제거하거나 자체 구현으로 대체하는 것이 아니라, 공개 Odyssey 코드가 사용한 Sentence Transformer의 checkpoint와 text-to-vector 변환 조건을 명시적으로 고정해 dependency 변경 뒤에도 같은 semantic skill retrieval을 재현할 수 있게 하는 것이다.

### 2. 감사에서 확인한 재현 위험

논문은 Sentence Transformer를 통한 query context encoding과 skill similarity retrieval을 설명하지만 정확한 checkpoint 이름은 명시하지 않는다. 반면 공개 코드의 `conf/config.json`은 `paraphrase-multilingual-MiniLM-L12-v2`를 지정한다. 따라서 이 모델은 **논문이 명시한 checkpoint가 아니라 공개 코드가 선택한 modernized 재현 기준**으로 구분해야 한다.

또한 기존 구현은 `HuggingFaceEmbeddings(model_name=...)`에 model 경로만 전달했다. 이 상태에서는 normalization, precision과 batch 설정이 설치된 Sentence Transformers·LangChain 버전의 기본값에 의존한다. 동일 model 파일을 사용하더라도 dependency 변화가 vector scale이나 retrieval score에 영향을 줄 가능성이 있었다.

마지막으로 `SkillManager`의 기본 retrieval 수는 5였지만 상위 `Odyssey` 생성자의 기본값은 10으로 남아 있어, 논문 본문의 top-5 skill selection 및 현재 profile 정책과 실제 runtime 기본값이 일치하지 않았다.

### 3. 수행 내용

#### 3.1 공개 코드 checkpoint의 provenance 고정

modernized baseline의 model ID를 `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`로 기록하고, 로컬 Hugging Face download metadata에서 revision을 다음과 같이 확인했다.

```text
e8f8c211226b894fcb81acc59f3b34ba3efd5f42
```

로컬 model directory에는 PyTorch, ONNX, OpenVINO와 TensorFlow용 중복 artifact가 함께 존재한다. 현재 Odyssey의 Sentence Transformer 실행에는 PyTorch safetensors 경로를 사용하므로, `model.safetensors`와 tokenizer·pooling·model config 등 runtime에 필요한 11개 파일만 canonical artifact로 정하고 각각의 크기와 SHA-256을 manifest에 기록했다. 사용하지 않는 변환·양자화 artifact는 재현 checksum 범위에서 제외했다.

#### 3.2 Query context와 skill description의 encoding 조건 고정

checkpoint 내부 설정과 현재 adapter 동작을 대조해 다음 text-to-vector contract를 고정했다.

| 항목 | 고정값 | 논문 기능상 의미 |
| --- | ---: | --- |
| vector dimension | 384 | query context와 skill description을 비교하는 공통 vector representation |
| maximum sequence length | 128 tokens | 긴 text 입력이 잘리는 동일한 경계 |
| pooling | attention-mask-aware mean pooling | token representation을 하나의 sentence representation으로 결합 |
| case folding | 사용하지 않음 | 입력 대소문자를 임의로 변경하지 않음 |
| normalization | 사용하지 않음 | 기존 공개 adapter의 vector scale을 보존 |
| precision | float32 | canonical embedding 계산 정밀도 |
| batch size | 32 | corpus encoding의 기본 처리 단위 |
| adapter preprocessing | newline을 ASCII space로 치환 | query와 description에 동일한 text 전처리 적용 |

query와 document는 서로 다른 encoder를 사용하지 않는다. LangChain adapter의 `embed_query`가 document encoding 경로를 공유하도록 유지해, subgoal과 skill description이 동일한 model·pooling·normalization 조건에서 비교되게 했다.

#### 3.3 Skill retrieval과 Planner QA retrieval의 encoder 설정 통일

기존에는 `SkillManager`와 `PlannerAgent`가 각각 `HuggingFaceEmbeddings`를 직접 생성했다. 두 경로가 dependency update 과정에서 서로 다른 설정을 갖지 않도록 공통 factory인 `odyssey/retrieval_embedding.py`를 추가했다.

두 retrieval 경로는 이제 다음 값을 명시적으로 공유한다.

- `normalize_embeddings=False`
- `precision="float32"`
- `batch_size=32`
- progress output 비활성화

또한 `Odyssey` runtime의 기본 skill retrieval 수를 논문 본문과 결정된 profile에 맞춰 top-5로 수정했다. top-10은 제거하지 않고 autonomous exploration 등을 위한 별도 retrieval profile로 남겨, 다음 단계에서 동일 corpus와 distance metric을 사용한 회귀 fixture로 검증한다.

#### 3.4 재현 manifest와 fixture 작성

`odyssey_semantic_encoder.json`에 model provenance, canonical artifact checksum, transformation contract, 관찰된 dependency version과 top-k 정책을 기록했다.

`semantic_encoder_fixture.py`는 두 단계로 실행된다.

1. **Static contract fixture:** model inference 없이 revision, 11개 artifact checksum, vector dimension, maximum sequence length, pooling과 source의 명시적 설정을 검사한다.
2. **Runtime contract fixture:** CPU에서 고정된 한국어·영어 문장을 실제로 encoding해 `(3, 384)` shape, NaN/Inf 부재, 반복 실행 오차와 newline/space 전처리 동등성을 검사한다.

현재 static contract fixture는 모든 항목을 통과했다. 실제 embedding runtime fixture는 연구자 실행 전이므로 semantic encoder 전체를 완료로 표시하지 않았다.

### 4. 당시 상태와 해석

| 논문상의 단계 | 당시 확보한 근거 | 상태 |
| --- | --- | --- |
| skill description을 vector representation으로 변환 | checkpoint·pooling·전처리·artifact checksum 고정 | 정적 검증 완료 |
| text-based subgoal을 query context로 encoding | skill description과 동일한 공통 encoder factory 적용 | 정적 검증 완료 |
| query context와 skill description의 similarity matching | distance metric과 실제 candidate 순위 미확정 | 다음 단계 |
| top-5 relevant skills 제시 | runtime 기본값을 top-5로 통일 | 정책·코드 반영 완료 |
| Actor가 적절한 code 선택 | MineMA Actor 연결 전 | 범위 밖·후속 단계 |

즉, 이 시점의 결과는 Odyssey의 semantic skill retrieval 전체 성공이 아니라, retrieval 입력을 생성하는 **semantic encoder 조건을 반복 가능한 상태로 고정한 것**이다. top-5/top-10 후보 결과, vector-store persist/reload와 Actor의 최종 skill selection은 별도 검증으로 남아 있었다.

### 5. 당시 다음 확인 작업

Minecraft server, Mineflayer bridge와 MineMA backend 없이 다음 명령을 연구자 실행 단계로 남겼다.

```bash
cd ~/Documents/MineSkynet
Odyssey/.venv/bin/python Odyssey/scripts/semantic_encoder_fixture.py --run-model --device cpu
```

당시 통과 기준은 세 입력의 384차원 vector 출력, finite 값, 반복 encoding 최대 절대 오차 `1e-6` 이하, newline/space 입력 동등성과 마지막 `PASS` 출력이었다. 이 실행 결과를 확보한 뒤 embedding checksum·vector norm과 현재 dependency 조합을 manifest에 기록하기로 했다.

### 6. 당시 근거 파일

- [Semantic encoder manifest](../manifest/odyssey_semantic_encoder.json)
- [Semantic encoder fixture](../../../MineSkynet-odyssey/Odyssey/scripts/semantic_encoder_fixture.py)
- [공통 retrieval encoder 설정](../../../MineSkynet-odyssey/Odyssey/odyssey/retrieval_embedding.py)
- [현대화 마일스톤](milestone_goal/modernization_milestone.md)
- [논문–코드–dependency 대응표](paper_code_dependency_map.md)

---

## 2026-08-27 — Semantic encoder runtime 및 top-5 retrieval 추가 보고

작성일: 2026-08-27  
대상 브랜치: `experiment/odyssey-modernized`

### 1. 추가 확인 목적

최초 보고에서 미실행으로 남긴 CPU encoder fixture를 수행하고, 고정한 checkpoint와 183개 skill description으로 논문의 query context encoding → similarity matching → top-5 relevant skills 흐름이 실제 동작하는지 확인했다.

### 2. Semantic encoder runtime 결과

CPU runtime fixture에서 세 입력이 `(3, 384)` float32 vector로 변환됐고, NaN/Inf가 없으며 반복 실행과 newline/space 입력의 최대 절대 오차가 모두 `0.0`임을 확인했다. 고정 입력 embedding의 SHA-256은 `4f5de76040931c0558f63c1e6083f6779c61f1611b81f9d456aa9b7263d32c6b`이다.

### 3. Semantic skill retrieval smoke test

기존 문서와 로그에는 query 원문, candidate 이름과 score가 함께 남은 실행 증거가 없었다. 따라서 고정한 encoder로 `skills.json`의 183개 skill description을 모두 Chroma에 indexing하고, 논문의 query context encoding → similarity matching → top-5 relevant skills 흐름을 직접 실행했다.

| Text-based subgoal/query context | 기대 skill | top-1 결과 | L2 score |
| --- | --- | --- | ---: |
| `Craft a wooden pickaxe.` | `craftWoodenPickaxe` | `craftWoodenPickaxe` | 16.1350 |
| `Mine diamond ore using an iron pickaxe.` | `mineDiamond` | `mineDiamond` | 11.6207 |
| `Breed two cows using wheat.` | `breedCow` | `breedCow` | 25.7432 |
| `밀을 사용해서 소 두 마리를 번식시킨다.` | `breedCow` | `breedCow` | 16.0217 |

183개 description이 모두 index에 들어갔고, 네 query 모두 기대 skill이 top-5에 포함됐을 뿐 아니라 rank 1로 반환됐다. 이 smoke set의 known-query recall@5는 `4/4 = 1.0`이다. 따라서 현재 고정 checkpoint와 corpus로 **실제 semantic skill retrieval이 가능하다**고 보고할 수 있다. 이는 네 개의 대표 query에 대한 기능 smoke 결과이며 전체 skill corpus의 일반적인 retrieval 정확도를 의미하지는 않는다.

표의 L2 score는 확률이나 정확도가 아니라 query vector와 description vector 사이의 거리이며, 같은 profile 안에서는 값이 작을수록 더 가까운 candidate다.

실행 중 다음 현대화 경고도 관찰했다.

- LangChain의 기존 `HuggingFaceEmbeddings` wrapper가 `langchain-huggingface`로 이전 예정이라는 deprecation 경고
- LangChain의 기존 Chroma wrapper가 `langchain-chroma`로 이전 예정이라는 deprecation 경고
- Chroma telemetry의 `capture()` signature 불일치 경고

세 경고는 이번 indexing과 candidate retrieval을 중단시키지 않았다. 그러나 구형 dependency issue로부터 안전한 실행환경을 만들기 위해 wrapper 지원 조합과 telemetry 설정은 후속 작업에서 정리해야 한다.

### 4. 현재 상태와 해석

| 논문상의 단계 | 현재 확보한 근거 | 상태 |
| --- | --- | --- |
| skill description을 vector representation으로 변환 | 183개 description 전체 indexing | runtime 검증 완료 |
| text-based subgoal을 query context로 encoding | 영어 3개·한국어 1개 query 실제 encoding | runtime 검증 완료 |
| query context와 skill description의 similarity matching | L2 top-5 candidate와 score 기록 | smoke 검증 완료 |
| top-5 relevant skills 제시 | 기대 skill rank 1: 4/4, recall@5: 1.0 | smoke 검증 완료 |
| Actor가 적절한 code 선택 | MineMA Actor 연결 전 | 범위 밖·후속 단계 |

즉, semantic encoder 조건 고정을 넘어 183개 공개 skill corpus에서 top-5 semantic retrieval이 실제로 동작함을 확인했다. 다만 이것은 제한된 known-query smoke test이며, 별도 top-10 profile, index persist/reload 뒤 candidate 순서 유지와 Actor의 최종 skill selection은 검증하지 않았다.

### 5. 재현 명령과 남은 작업

Minecraft server, Mineflayer bridge와 MineMA backend 없이 다음 명령으로 encoder와 top-5 retrieval 결과를 각각 재현할 수 있다.

```bash
cd ~/Documents/MineSkynet
Odyssey/.venv/bin/python Odyssey/scripts/semantic_encoder_fixture.py --run-model --device cpu
Odyssey/.venv/bin/python Odyssey/scripts/semantic_retrieval_smoke.py
```

두 fixture는 2026-08-27 CPU 실행에서 통과했다. 다음에는 같은 corpus·encoder·metric에서 top-10을 별도 profile로 실행하고, 저장한 Chroma index를 다시 열어도 candidate 순서가 유지되는지 확인한다. LangChain embedding/Chroma wrapper의 deprecated API와 telemetry warning도 기능 회귀를 유지하면서 정리해야 한다.

### 6. 추가 보고 근거 파일

- [Semantic encoder manifest](../manifest/odyssey_semantic_encoder.json)
- [Semantic encoder fixture](../../../MineSkynet-odyssey/Odyssey/scripts/semantic_encoder_fixture.py)
- [Semantic retrieval smoke fixture](../../../MineSkynet-odyssey/Odyssey/scripts/semantic_retrieval_smoke.py)
- [Semantic retrieval 실행 로그](../log/semantic_retrieval_smoke_2026-08-27.json)
- [공통 retrieval encoder 설정](../../../MineSkynet-odyssey/Odyssey/odyssey/retrieval_embedding.py)
- [현대화 마일스톤](milestone_goal/modernization_milestone.md)
- [논문–코드–dependency 대응표](paper_code_dependency_map.md)

---

## 2026-08-27 — Retrieval fixture 완성

작성일: 2026-08-27  
대상 브랜치: `experiment/odyssey-modernized`

### 1. 논문상 기능과 이번 작업의 목적

Odyssey는 Planner의 text-based subgoal을 query context로 encoding하고, open-world skill library의 description vector와 similarity matching해 relevant skills를 Actor에게 제시한다. 이번 작업은 이 semantic skill retrieval을 다음 두 실행 profile과 반복 가능한 vector-store contract로 고정하는 것이 목적이다.

- 기본 `top5`: 논문 본문의 Actor candidate selection 조건이자 연산 부담을 줄인 기본 profile
- 별도 `top10`: 부록과 autonomous exploration 조건을 보존하는 확장 profile

검증 대상은 자연어 subgoal → 183개 description index → 순서와 score를 가진 candidate 반환까지다. MineMA Actor의 최종 선택과 Minecraft skill 실행은 이번 fixture의 범위가 아니다.

### 2. 구현한 retrieval contract

공통 retrieval 설정에 `top5=5`, `top10=10` profile과 기본 profile `top5`를 명시했다. `SkillManager`와 상위 `Odyssey` 생성자는 이 기본값을 공유하며, Chroma collection의 distance metric은 `L2`로 고정했다.

Fixture는 임시 persist directory에서 183개 description의 index를 새로 만들고 검색한 뒤, 첫 프로세스를 종료한다. 이후 별도 프로세스가 같은 저장 index를 다시 열어 동일 query와 profile을 검색한다. 이 구조는 같은 in-memory object를 반복 호출한 결과가 아니라 실제 index 재로드 뒤의 결과를 비교한다.

### 3. 대표 자연어 subgoal 결과

영어 세 개와 한국어 한 개의 대표 query를 사용했다. fresh index와 reloaded index에서 결과가 같았으므로 아래에는 top-1과 fresh index의 score를 요약한다. 각 query의 top-10 전체 후보와 score는 실행 로그에 저장했다.

| Text-based subgoal/query context | 기대 skill | top-1 결과 | L2 score |
| --- | --- | --- | ---: |
| `Craft a wooden pickaxe.` | `craftWoodenPickaxe` | `craftWoodenPickaxe` | 16.1350 |
| `Mine diamond ore using an iron pickaxe.` | `mineDiamond` | `mineDiamond` | 11.6207 |
| `Breed two cows using wheat.` | `breedCow` | `breedCow` | 25.7432 |
| `밀을 사용해서 소 두 마리를 번식시킨다.` | `breedCow` | `breedCow` | 16.0217 |

L2 score는 확률이나 정확도가 아니라 query와 description vector 사이의 거리다. 같은 profile에서는 값이 작을수록 semantic closeness가 높다.

### 4. Profile과 index reload 결과

| 검사 | Fresh index | Reloaded index | 판정 |
| --- | ---: | ---: | --- |
| corpus/index 수 | 183 | 183 | 통과 |
| top-5 known-query recall@5 | 4/4 | 4/4 | 통과 |
| top-10 known-query recall@10 | 4/4 | 4/4 | 통과 |
| top-5가 top-10의 1~5위와 일치 | 4/4 | 4/4 | 통과 |
| fresh/reload candidate 순서 | 비교 기준 | 두 profile·네 query 전부 동일 | 통과 |
| fresh/reload 최대 score 차이 | 비교 기준 | `0.0` | 통과 |

따라서 고정한 encoder·183개 corpus·L2 조건에서 기본 top-5와 별도 top-10 retrieval이 모두 가능하며, index를 재생성하고 저장본을 다시 연 뒤에도 후보 순서와 score가 유지된다고 보고할 수 있다. 이는 네 known query에 대한 retrieval contract 회귀이며 전체 183개 skill의 일반적인 검색 정확도나 Actor 선택 성공률을 의미하지 않는다.

### 5. 관찰된 경고와 남은 작업

이번 경고는 현재 semantic retrieval 결과가 틀렸다는 뜻은 아니다. 다만 지금 사용한 library 연결부가 향후 update나 새 설치 환경에서 같은 기능을 계속 제공한다는 보장이 약하다는 신호이므로, 구형 dependency issue로부터 안전한 연구 기반을 만들기 위해 정리해야 한다.

| 용어·경고 | 간략한 의미 | 위험한 이유 |
| --- | --- | --- |
| `wrapper` | Odyssey 코드가 Sentence Transformer나 Chroma의 내부 API를 직접 다루지 않도록 LangChain이 중간에서 공통 interface로 감싼 adapter다. | wrapper가 바뀌면 model과 DB 자체가 정상이어도 import 경로, 설정 전달 또는 반환 score 형식이 달라져 retrieval 고리가 끊길 수 있다. |
| `deprecation` | 현재는 동작하지만 해당 class·import 경로를 앞으로 제거할 예정이라는 유지보수 경고다. | 지금 무시해도 즉시 실패하지 않지만, 이후 LangChain upgrade에서 `HuggingFaceEmbeddings`나 `Chroma` class가 삭제되면 clean install 또는 실행이 중단될 수 있다. |
| `langchain-huggingface` | Hugging Face embedding wrapper를 LangChain 본체에서 분리해 관리하는 새 공식 package다. | 기존 wrapper와 model option·version 호환성이 완전히 같다고 가정하고 교체하면 vector scale이나 전처리가 달라져 candidate score·순위가 조용히 바뀔 수 있다. |
| `langchain-chroma` | Chroma vector DB 연결 wrapper를 별도 package로 옮긴 새 공식 package다. | Chroma client의 저장 방식, collection 설정이나 score 반환 계약이 달라지면 기존 index를 열지 못하거나 재로드 뒤 후보 순서가 바뀔 수 있다. |
| `telemetry` | Chroma가 client 시작이나 collection 추가 같은 사용 event를 수집·전송하려는 진단 기능이며 skill description이나 embedding 계산 자체는 아니다. | 연구 기능에는 불필요한 외부 동작이고, 실패 메시지가 반복되면 실제 DB 오류를 로그에서 가리거나 제한된 network 환경에서 불필요한 실패 원인이 될 수 있다. |
| `capture() signature` 불일치 | telemetry event를 보내는 쪽과 받는 함수가 기대하는 인자 개수가 다르다는 뜻으로, 관련 package version 조합이 맞지 않음을 보여준다. | 현재는 telemetry만 실패했지만 같은 dependency 조합의 다른 API에서도 호환성 문제가 잠복했을 가능성이 있으며, warning을 error로 처리하는 환경에서는 실행을 막을 수 있다. |
| `clean environment`와 `exact lock` | 기존 cache나 우연히 설치된 package 없이 새 환경을 만들고, 검증한 package의 정확한 version 조합만 다시 설치하는 절차다. | 현재 `.venv`에만 존재하는 간접 dependency 덕분에 우연히 통과한 경우 다른 PC나 재설치에서 재현되지 않는다. version을 고정하지 않으면 같은 명령도 설치 시점에 따라 다른 결과를 낼 수 있다. |

이번 실행에서는 위 경고가 index 생성·persist·reload와 검색을 중단시키지 않았고, fresh/reload 후보 순서와 score도 일치했다. 따라서 현재 retrieval fixture는 통과로 유지하되 dependency 안전성은 완료로 올리지 않는다.

다음 dependency 정비에서는 `langchain-huggingface`와 `langchain-chroma`의 지원 version 조합을 별도 환경에서 검토하고, encoder vector contract와 이번 retrieval fixture를 모두 통과한 조합만 lock한다. telemetry는 끄거나 호환되는 version으로 맞추되, 경고를 숨기는 것만으로 해결했다고 판정하지 않는다. 별도 clean environment의 exact lock 설치와 재실행은 아직 완료하지 않았다.

### 6. 재현 명령과 근거 파일

```bash
cd ~/Documents/MineSkynet
Odyssey/.venv/bin/python Odyssey/scripts/semantic_retrieval_fixture.py
```

- [Retrieval profile fixture](../../../MineSkynet-odyssey/Odyssey/scripts/semantic_retrieval_fixture.py)
- [Top-5·top-10 후보와 reload 실행 로그](../log/semantic_retrieval_profiles_2026-08-27.json)
- [Semantic encoder·retrieval manifest](../manifest/odyssey_semantic_encoder.json)
- [공통 retrieval profile 설정](../../../MineSkynet-odyssey/Odyssey/odyssey/retrieval_embedding.py)
- [현대화 마일스톤](milestone_goal/modernization_milestone.md)
- [논문–코드–dependency 대응표](paper_code_dependency_map.md)

---

## 2026-08-27 — Retrieval wrapper migration 작업 기준

작성일: 2026-08-27
기준 커밋: `9d626f6`

### 1. 브랜치와 과거 기준점

- 임시 작업 브랜치 `experiment/retrieval-wrapper-migration`: `langchain-huggingface`와 `langchain-chroma` 이전, telemetry 정리와 clean-install 후보 검증만 수행한다.
- 과거 기준 annotated tag `odyssey-modernized-retrieval-legacy-wrapper`: 기존 LangChain community wrapper로 encoder와 top-5·top-10 fresh/reload fixture를 통과한 `9d626f6`을 변경 없이 보존한다.
- 기준 브랜치 `experiment/odyssey-modernized`: migration 결과가 합격하기 전까지 기존 검증 상태를 유지한다.

### 2. 병합 기준

신규 wrapper 조합은 기존과 같은 encoder revision·183개 corpus·L2 조건에서 encoder contract, top-5 기본·top-10 별도 profile, fresh index와 별도 프로세스 reload를 모두 통과해야 한다. 후보 순서와 score 차이를 legacy-wrapper tag 결과와 비교하고, telemetry 경고가 실제로 제거됐으며 exact version의 clean-install 후보를 제시해야 한다.

위 조건을 충족하고 연구자가 최종 dependency 조합을 승인한 뒤에만 임시 브랜치를 `experiment/odyssey-modernized`에 병합한다. 승인 전에는 기존 작동 조합을 제거하거나 신규 조합을 최종 lock으로 확정하지 않는다. 병합 뒤 임시 브랜치는 삭제하되 과거 상태는 tag와 이 보고 기록으로 보존한다.

---

## 2026-08-27 — Retrieval wrapper migration clean-install 검증

작성일: 2026-08-27
작업 브랜치: `experiment/retrieval-wrapper-migration`
비교 기준: `odyssey-modernized-retrieval-legacy-wrapper` (`9d626f6`)

### 1. 논문상 기능과 작업 목적

이번 작업은 자연어 subgoal과 183개 skill description을 같은 encoder로 변환하고 semantic closeness 순으로 candidate를 제시하는 Odyssey 기능을 보존하면서, 제거 예정인 LangChain community wrapper와 Chroma 0.3 저장 고리를 지원되는 공식 partner package로 분리할 수 있는지 확인했다.

현대화의 판정 대상은 새 package가 더 빠른지가 아니라 다음 retrieval contract의 보존 여부다.

- 공개 코드 checkpoint와 text-to-vector 변환 조건 유지
- top-5 기본·top-10 별도 profile 유지
- 183개 corpus의 candidate 순서와 L2 score 관찰
- fresh index와 별도 프로세스 reload의 동일성
- clean install과 telemetry·deprecated warning 제거

### 2. 호출 지점과 version 결합 감사

기존 환경은 `langchain 0.2.17`, `langchain-community 0.2.19`, `langchain-core 0.2.43`, `chromadb 0.3.29`와 `posthog 7.27.0`을 사용했다. 실제 호출은 다음 세 고리에 있었다.

1. `retrieval_embedding.py`: community `HuggingFaceEmbeddings` 생성
2. `SkillManager`와 `PlannerAgent`: community `Chroma` 생성 및 저장
3. Actor·Planner·Critic 등: `langchain.schema` message class import

`chromadb 0.3.29`는 `posthog`의 상한을 고정하지 않아 현재 `posthog 7.27.0`과 함께 설치됐고, telemetry `capture()` 인자 규약이 맞지 않았다. `pip check`는 package metadata상 의존성 범위만 확인하므로 이 runtime API 불일치를 탐지하지 못했다.

최신 공식 partner package의 요구 조건은 기존 `langchain-core 0.2`와 직접 공존하지 않았다. `langchain-huggingface 1.2.2`는 `langchain-core >=1.2.31`, `langchain-chroma 1.1.0`은 `chromadb >=1.3.5`와 `langchain-core >=1.1.3`을 요구했다. 따라서 import 두 줄만 바꾸지 않고 message class를 `langchain-core`로 옮기고 retrieval wrapper를 profile 경계에서 lazy import하도록 수정했다.

### 3. 기존 API와 신규 API contract 비교

| 항목 | Legacy community wrapper | Modern partner wrapper | 처리 |
| --- | --- | --- | --- |
| embedding class | `langchain_community.HuggingFaceEmbeddings` | `langchain_huggingface.HuggingFaceEmbeddings` | profile별 lazy import |
| model 인자 | `model_name=` | `model=` | 공통 factory에서 차이 흡수 |
| encoding 설정 | `encode_kwargs` | `encode_kwargs` | batch 32·float32·normalization 없음 유지 |
| Chroma class | community `Chroma` | `langchain_chroma.Chroma` | 공통 vector-store factory에서 분기 |
| persistence | DuckDB+Parquet와 명시적 `.persist()` | `PersistentClient`와 쓰기 시 자동 저장 | modern profile에서는 `.persist()` 호출 제거 |
| score 반환 | `similarity_search_with_score`의 distance | 동일 method의 distance | L2·candidate·score를 fixture로 비교 |
| telemetry | 기본 활성 및 `capture()` warning | `Settings(anonymized_telemetry=False)` | modern profile에서 warning 부재를 합격 조건으로 검사 |

공식 Chroma migration 문서에 따르면 0.4부터 저장 형식이 DuckDB+Parquet에서 SQLite 기반으로 바뀌고 수동 `.persist()`가 제거됐다. 기존 index는 원본 연구 자산이 아니라 고정 corpus에서 재생성 가능한 파생물이므로 migration하지 않고 183개 description에서 새로 만들었다.

### 4. 별도 시험 profile과 clean-install lock 후보

기존 조합을 제거하지 않고 `legacy-community`와 `modern-partner` 두 wrapper profile을 추가해 시험했다. 검증과 연구자 승인 뒤 `modern-partner`를 modernized 기본값으로 전환했으며 legacy 상태는 기준 tag로 보존한다.

Python 3.10.20의 빈 임시 환경에서 다음 핵심 조합을 설치했다.

| Package | Candidate version |
| --- | ---: |
| `langchain-core` | 1.6.0 |
| `langchain-huggingface` | 1.2.2 |
| `langchain-chroma` | 1.1.0 |
| `chromadb` | 1.3.5 |
| `posthog` | 5.4.0 |
| `sentence-transformers` | 5.6.0 |
| `transformers` | 5.14.1 |
| `torch` | 2.13.0+cpu |
| `huggingface-hub` | 1.24.0 |
| `tokenizers` | 0.22.2 |
| `numpy` | 1.26.4 |

첫 빈 환경의 전체 resolved version을 lock 후보에 기록한 뒤, 두 번째 빈 환경에 CPU PyTorch와 이 파일을 그대로 설치했다. 두 환경 모두 `pip check`에서 broken requirement가 없었다. 승인 뒤 파일을 `requirements-retrieval-modern.lock.txt`로 고정하고 기본 `requirements.txt`에서 참조하도록 연결했다. 최종 lock SHA-256은 `3fd810577c7f2bb40116bca05fa2b4f2a0bc481c7c0f713b046fbc94a463dbb2`다.

### 5. Encoder·retrieval·warning 결과

두 번째 clean 환경에서 encoder fixture는 `(3, 384)` float32, 반복 오차 `0.0`, newline/space 오차 `0.0`과 기존과 같은 embedding SHA-256 `4f5de76040931c0558f63c1e6083f6779c61f1611b81f9d456aa9b7263d32c6b`로 통과했다. 즉 wrapper 교체가 text-to-vector 결과를 바꾸지 않았다.

신규 Chroma index의 독립 fixture 결과는 다음과 같다.

| 검사 | 결과 |
| --- | ---: |
| index count | 183 |
| fresh top-5 recall@5 | 4/4 |
| fresh top-10 recall@10 | 4/4 |
| reload top-5·top-10 recall | 각각 4/4 |
| fresh/reload candidate 순서 | 전부 동일 |
| fresh/reload 최대 score 차이 | `0.0` |
| deprecated wrapper warning | 없음 |
| telemetry warning | 없음 |

따라서 신규 partner wrapper 자체의 encoder → index 생성 → reload → 검색 contract와 telemetry 비활성화는 통과했다.

### 6. Legacy 대비 score 차이와 최종 판단

Legacy와 modern의 top-10 후보 순서는 네 query에서 모두 같았지만 L2 score는 다음만큼 달랐다.

| Query | Legacy–modern 최대 절대 score 차이 |
| --- | ---: |
| `Craft a wooden pickaxe.` | `1.9073486328125e-06` |
| `Mine diamond ore using an iron pickaxe.` | `2.86102294921875e-06` |
| `Breed two cows using wheat.` | `7.62939453125e-06` |
| `밀을 사용해서 소 두 마리를 번식시킨다.` | `3.814697265625e-06` |

전체 최대 차이 `7.62939453125e-06`은 사전에 제안한 절대 허용값 `1e-6`을 넘었다. 그러나 이 값은 동일 구현의 반복 안정성을 확인하기 위한 임시 기준이었고 서로 다른 Chroma 구현의 동등성 기준으로 삼을 근거는 확인되지 않았다. Encoder byte checksum과 모든 후보 순서가 같고 각 modern index의 fresh/reload score는 정확히 같으므로, 이 차이는 stochastic한 변화가 아닌 dependency 내부 L2 수치 구현 차이로 기록한다.

현대화 자체의 성능 비교가 연구 목적이 아니므로 별도의 절대 허용값을 사후 설정하지 않는다. 논문 기능에 직접 대응하는 embedding checksum, top-k 후보 순서와 recall 보존, 동일 modern profile의 fresh/reload score 동일성, clean install과 warning 제거를 병합 기준으로 삼아 modern profile을 승인했다. 관찰된 raw score 차이는 숨기지 않고 진단값으로만 보존한다.

### 7. 근거와 공식 참고자료

- [Migration 실행 로그](../log/retrieval_wrapper_migration_2026-08-27.json)
- [Modern retrieval lock](../../../MineSkynet-odyssey/Odyssey/requirements-retrieval-modern.lock.txt)
- [공통 wrapper profile factory](../../../MineSkynet-odyssey/Odyssey/odyssey/retrieval_embedding.py)
- [Retrieval comparison fixture](../../../MineSkynet-odyssey/Odyssey/scripts/semantic_retrieval_fixture.py)
- [LangChain HuggingFace encode contract](https://reference.langchain.com/python/langchain-huggingface/embeddings/huggingface/HuggingFaceEmbeddings/encode_kwargs)
- [LangChain Chroma API](https://reference.langchain.com/python/langchain-chroma/vectorstores/Chroma)
- [Chroma persistence migration](https://docs.trychroma.com/docs/overview/migration)

---

## 2026-08-27 — Primitive 40 runtime 전 코드 감사

작성일: 2026-08-27
대상 브랜치: `experiment/odyssey-modernized`
범위: 실제 Minecraft fixture를 추가하기 전에 논문 contract, working manifest, JavaScript source와 modern bridge dependency를 대조

### 1. 논문상 기능과 현재 증거

Odyssey의 primitive 40개는 183개 compositional skill이 Minecraft 상태를 바꾸기 위해 사용하는 하위 interface다. 이번 감사는 40개를 모두 온라인으로 실행하는 것이 아니라, 실행 전에 정상 입력에서도 실패할 명백한 오류와 공개 코드의 설계 선택일 수 있어 연구자 의도 확인이 필요한 차이를 분리했다.

- Odyssey 추가 primitive 22개와 Voyager 상속 custom primitive 8개 및 지원 함수는 모두 JavaScript syntax 검사를 통과했다.
- Voyager에서 직접 사용하는 Mineflayer API 10개는 현재 Mineflayer 4.25.0과 pathfinder source에서 interface 존재를 확인했다.
- `goto`와 `getAnimal`은 offline 14/14와 Minecraft online fixture를 통과했다.
- 기존 E0의 원목·작업대 반복 fixture는 `mineBlock`, `craftItem`, `getPlanksCount`와 `exploreUntil`의 일부 실행 경로를 간접적으로 통과했다. 다만 `exploreUntil`의 실제 이동·timeout branch까지 모두 검증한 것은 아니다.

### 2. 명백한 오류

아래 항목은 연구 의도와 무관하게 현재 dependency에서 존재하지 않는 API를 호출하거나, 정상적인 실패 조건 뒤에도 실행을 계속하거나, 선언되지 않은 상태를 사용하는 결함이다. 수정 뒤 offline regression을 먼저 통과해야 한다.

| Primitive·계층 | 코드상 오류 | 예상 결과 |
| --- | --- | --- |
| `killMob`·combat bridge | `killMob`은 `bot.pvp`와 `bot.hawkEye`를 호출하지만 modern bridge는 두 plugin을 설치·load하지 않는다. Legacy에는 `mineflayer-pvp 1.3.2`, `minecrafthawkeye 1.3.6`이 있었다. | entity가 존재하는 실제 전투에서 undefined API 오류 |
| `getItemFromChest` | 설치된 Mineflayer 4.25.0 container에는 없는 `chest.findContainerItem()`을 호출한다. 현재 API는 `containerItems()`, `withdraw()`, `deposit()` 경로다. | chest를 정상적으로 열어도 인출 단계에서 오류 |
| `feedAnimals` | 종별 먹이를 조회하거나 hand에 장착하지 않고 `bot.useOn(animal)`을 호출한다. | 논문의 “appropriate food로 먹인다”는 contract를 수행하지 못함 |
| `cookFood` | coal이 없다는 메시지를 낸 뒤 return하지 않고 furnace 배치와 `smeltItem`을 계속 호출한다. 완료 메시지도 실제 `count`와 무관하게 항상 1개라고 기록한다. | 실패를 성공처럼 이어가거나 잘못된 결과 보고 |
| `killMonsters` | `isAlive`와 반복 변수 `i`를 선언하지 않고, target이 `null`이어도 `monster.position`을 참조하며, death listener를 제거하지 않는다. | 전역 상태 오염, null dereference와 반복 실행 listener 누적 |
| `plantSeeds` | `findBlocks()`의 빈 배열을 `if (!farmland)`로 검사하고 seed 존재를 확인하지 않은 채 equip한다. | farmland·seed가 없는 failure path가 의도대로 종료되지 않음 |
| `eatFood` | 지정 food가 inventory에 없는 경우를 확인하지 않고 `bot.equip(null, "hand")`을 호출한다. | 정상적인 missing-item 조건이 구조화되지 않은 runtime 오류가 됨 |
| `findSuitablePosition` | 세 높이 층의 offset 목록에 `(-1, *, 1)`이 중복되고 대응하는 `(1, *, -1)`이 누락됐다. | 탐색 영역이 의도치 않게 비대칭이 됨 |

`killAnimal`은 자체 syntax보다 `killMob`의 누락 combat plugin에 의해 함께 막힌다. `killMonsters` 또한 같은 blocker를 공유하므로 combat dependency를 복구하거나 별도 지원 profile로 고정하기 전에는 online 성공을 주장할 수 없다.

### 3. 연구자 의도 확인 또는 fixture로 판별할 영역

아래 항목은 위험이 보이지만 공개 코드가 의도적으로 택한 동작일 가능성을 배제할 수 없다. 임의 수정하지 않고 논문 contract와 기존 compositional caller를 함께 보존하는 방향을 정한 뒤 처리한다.

| 항목 | 논문·구현 차이 | 판단할 내용 |
| --- | --- | --- |
| spatial signature | 논문의 `checkBlockAbove`·`checkBlocksAround`은 `(x,y,z)`를 받지만 공개 코드와 기존 compositional skill은 `Vec3`를 전달한다. | 기존 `Vec3` caller를 유지하면서 좌표 signature도 받는 호환 interface로 만들지 결정 |
| placement target | 논문의 `findSuitablePosition`은 대상 block이 `air`여야 하지만 구현과 기존 manifest는 `air` 또는 `water`를 허용한다. | 논문 contract대로 air만 허용할지, water 허용을 공개 코드 profile로 보존할지 결정 |
| pathfinder goal | `plantSeeds`와 `feedAnimals`는 점유된 farmland·entity 좌표에 `GoalBlock`을 사용한다. | 실제 접근 실패인지 online fixture로 확인하고 `GoalNear`·`GoalLookAtBlock` 전환 여부 결정 |
| armor 우선순위 | `equipArmor`는 diamond → iron → gold → chainmail → leather 순이다. “best”가 방어력, 재료 tier 또는 공개 코드 순서를 뜻하는지 명시되지 않았다. | 논문 재현에서는 공개 순서를 보존할지 게임 수치 순으로 정렬할지 결정 |
| drop 회수 책임 | `killMob`이 drop을 수집한 뒤 `killAnimal`이 과거 entity 위치로 다시 이동하고 수집 완료를 출력한다. | primitive 간 책임 중복을 제거할지 공개 orchestration을 유지할지 결정 |
| combat command | `killMonsters`가 `/gamemode survival`을 직접 호출한다. | 일반 primitive에서 OP command를 허용할지, controlled combat profile에만 둘지 결정 |
| exploration randomness | `exploreUntil`은 `Math.random()`으로 10~29 block 이동량을 정한다. | production 탐색은 유지하되 fixture에서 RNG를 주입·고정할지 결정 |

#### 쟁점 이해를 위한 설명과 예시

`Vec3`는 Minecraft의 `(x,y,z)` 좌표를 하나의 3차원 vector 객체로 묶은 자료형이다. 예를 들어 `new Vec3(10, 64, -5)`는 `x=10`, `y=64`, `z=-5`를 가지며, `position.plus(new Vec3(0, 1, 0))`은 바로 위 좌표를, `position.distanceTo(other)`는 다른 위치까지의 거리를 계산한다. 논문의 `checkBlockAbove(bot, "air", 10, 64, -5)`와 공개 코드의 `checkBlockAbove(bot, "air", new Vec3(10, 64, -5))`는 같은 위치를 전달하지만 parameter 표현이 다르다.

`findSuitablePosition`은 crafting table, furnace와 chest 같은 장치를 놓기 전에 bot 주변의 후보 좌표를 순서대로 검사하는 함수다. 후보 위치의 block이 비어 있고 주변 6방향 중 흙·돌처럼 장치를 붙일 reference block이 하나 이상 있으면 해당 좌표를 반환한다. 상위 skill은 `const position = await findSuitablePosition(bot)`으로 좌표를 받은 뒤 `placeItem(bot, "furnace", position)`처럼 사용한다. 따라서 이 함수의 결과는 다수의 crafting·smelting·storage skill의 배치 성공에 함께 영향을 준다. 논문은 대상 위치를 `air`로 설명하지만 공개 구현은 `air`와 `water`를 모두 후보로 검사한다.

`GoalBlock(x,y,z)`은 일반적으로 bot의 발 위치가 지정 block 좌표에 도달하도록 요구하는 pathfinder goal이다. `plantSeeds`는 이미 farmland block이 차지한 좌표를, `feedAnimals`는 계속 움직일 수 있는 entity 좌표를 이 goal에 넣는다. Source만으로 실제 pathfinder의 도달 판정을 확정할 수 없어, 이 항목은 정적 입력·실패 처리와 분리해 Minecraft 상태에서 관찰해야 한다.

`equipArmor`의 “best”는 하나의 수치로 명시돼 있지 않다. 공개 구현은 diamond → iron → gold → chainmail → leather 순으로 먼저 발견한 장비를 선택한다. Minecraft에서는 재료 등급이 대체로 방호력·내구도와 함께 올라가지만 gold는 예외이며, chainmail은 gold보다 내구도가 높고 leggings는 방호력도 더 높다. 따라서 “best”가 공개 코드의 재료 나열 순서인지 실제 방호력·내구도인지에 따라 gold와 chainmail의 상대 순서가 달라진다.

`killAnimal`과 `killMob`의 책임 중복은 다음 상황에서 드러난다. Cow A가 `(10,64,5)`, Cow B가 `(12,64,5)`에 있을 때 `killAnimal`이 먼저 Cow A를 기억하더라도, 내부의 `killMob("cow")`은 `nearestEntity()`를 다시 호출하므로 이동과 거리 변화 뒤 Cow B를 선택할 수 있다. `killMob`이 Cow B를 죽이고 beef·leather까지 수집한 뒤에도 `killAnimal`은 처음 기억한 Cow A의 과거 위치로 이동하고 실제 추가 수집 여부와 관계없이 `Collected dropped items.`를 출력한다. 이 경우 선택 대상, 실제 처치 대상과 성공 메시지가 서로 다를 수 있다.

`/gamemode survival`은 일반 chat이 아니라 OP 권한이 필요한 server command다. 생성된 JavaScript는 전체 `bot` 객체를 받으므로, bot이 OP라면 논리적으로 `bot.chat("/gamemode creative")`, `bot.chat("/give @s diamond 64")` 또는 `bot.chat("/tp @s ...")` 같은 command도 실행할 수 있다. Planner나 orchestrator가 정상적으로 subgoal만 생성할 것이라는 기대와 별개로, 현재 interface 자체는 `/`로 시작하는 command를 기술적으로 차단하지 않는다.

`exploreUntil`의 이동 거리는 `Math.floor(Math.random() * 20 + 10)`으로 계산돼 호출할 때마다 10~29 block 사이에서 달라진다. Production에서는 같은 방향을 탐색해도 12칸 또는 25칸처럼 서로 다른 goal이 만들어질 수 있다. Offline fixture에서 `Math.random()`의 반환값을 잠시 `0`으로 두면 항상 10 block, `0.999`로 두면 항상 29 block이 계산되므로 goal 좌표, cleanup과 timeout 분기를 반복해서 같은 조건으로 관찰할 수 있다. 이는 production 탐색을 고정한다는 뜻이 아니라 fixture 안에서만 난수 결과를 예측 가능하게 만든다는 뜻이다.

이 구분에서 “의도 확인”은 오류 가능성이 낮다는 뜻이 아니다. 논문과 공개 코드 중 어느 쪽을 modernized contract로 삼을지 결정해야 수정 방향이 달라진다는 뜻이다. 특히 `GoalBlock` 접근은 source만으로 실패를 단정하지 않고 Minecraft fixture로 판별한다.

### 4. 권장 검증 순서

1. Spatial·inventory·equipment·count처럼 server가 필요 없는 primitive를 mock bot offline fixture로 묶는다.
2. 위 명백한 오류를 수정하고 성공, 입력 누락, 빈 검색 결과와 실패 후 상태를 회귀로 고정한다.
3. Voyager custom primitive의 placement, smelting과 chest contract를 offline interface fixture로 확인한다.
4. Mineflayer 직접 API 10개는 각각 별도 서버를 띄우지 않고 farming, consume, fishing, sleeping과 entity interaction 대표 fixture로 묶는다.
5. Minecraft online 검증은 farming, placement/cooking, storage, inventory/equipment와 combat의 기능군 단위로 수행한다. Combat은 dependency와 `/gamemode` 정책을 확정한 뒤 마지막에 분리한다.

따라서 최종 `40/40`은 모든 항목에 적어도 syntax·offline contract 또는 direct-interface 증거가 있고, 실제 world state가 필요한 기능군에 대표 online fixture가 있을 때 표시한다. 38개를 각각 별도 online 실행하는 방식은 요구하지 않는다.

### 5. 근거 파일

- [Primitive 40 working manifest](../manifest/odyssey_primitive_40.json)
- [현재 primitive offline fixture](../../../MineSkynet-odyssey/Odyssey/scripts/primitive_runtime_offline.js)
- [현재 primitive online fixture](../../../MineSkynet-odyssey/Odyssey/scripts/primitive_runtime_online.py)
- [Odyssey 추가 primitive source](../../../MineSkynet-odyssey/Odyssey/skill_library/skill/primitive)
- [Voyager 상속 control primitive source](../../../MineSkynet-odyssey/Odyssey/odyssey/control_primitives)
- [Modern Mineflayer bridge](../../../MineSkynet-odyssey/Odyssey/odyssey/env/mineflayer/index.js)

---

## 2026-08-27 — Primitive 명백 오류 전 선행 정책 6항목

작성일: 2026-08-27
대상 브랜치: `experiment/odyssey-modernized`
범위: 연구자가 확정한 공개-code contract와 실행 권한 경계를 명백 오류 수정 전에 고정. `plantSeeds`·`feedAnimals`의 Pathfinder goal은 이 단계에서 변경하지 않음

### 1. 논문 기능에 대응하는 한 줄 설명

Compositional skill이 공유하는 primitive의 입력 형식·배치 조건·장비 선택·전투 후처리·탐색 난수와 서버 권한 경계를 먼저 고정해, 이후 결함 수정이 공개 Odyssey의 행동 의미를 임의로 바꾸지 않게 했다.

### 2. 확정한 contract와 구현

| 항목 | modernized contract | 구현·증거 |
| --- | --- | --- |
| Spatial position | 공개 compositional caller와 같은 `Vec3`를 사용 | `checkBlockAbove`·`checkBlocksAround`의 `Vec3` 입력과 plain object 거부를 offline fixture로 확인 |
| Placement target | 공개 코드 우선으로 `findSuitablePosition`의 `air` 또는 `water` 후보를 유지 | 인접 reference block이 있는 water 좌표가 반환되는 fixture 통과 |
| Armor order | 사용자가 이해하기 쉬운 공개 재료 순서 diamond → iron → gold → chainmail → leather 유지 | 네 armor slot 모두 gold와 chainmail이 함께 있을 때 gold가 선택됨을 확인 |
| Drop ownership | `killMob`이 target 선택·처치·drop 회수와 결과를 소유하고 `killAnimal`은 sword 장착 뒤 한 번만 위임 | `killAnimal`의 과거 entity 재이동과 중복 수집 메시지를 제거하고 단일 위임 fixture 통과 |
| Server operator boundary | 실행 bot은 non-OP, world 준비·gamemode·summon·reset은 연구자/서버 호스트의 container-local RCON harness가 담당 | modernized `ops.json=[]`, generated skill의 `/` command 차단, hard reset·inventory injection 거부, `host_admin_rcon.py` 추가 |
| Exploration randomness | episode seed 42에서 시작하는 재현 가능한 의사난수 sequence를 사용하되 탐색 거리는 계속 10~29 block 사이에서 변함 | 같은 seed의 8개 값이 일치하고 값들이 고정 상수가 아님을 fixture로 확인 |

`42`는 특별한 Minecraft 의미나 성능 근거가 있는 값이 아니라, 동일한 탐색 조건을 다시 만들기 위한 명시적 기본 seed다. 구현은 32-bit LCG 상태를 episode마다 42로 초기화하며 `/health`에 seed와 현재 RNG state를 노출한다.

### 3. 권한 격리의 의미

Node wrapper의 `/` 차단만으로 보안을 주장하지 않는다. 최종 권한 경계는 Minecraft server의 빈 operator 목록이다. 실행 bot이 잘못 생성된 `bot.chat("/give ...")` 코드를 전달받더라도 server 권한으로 관리자 명령을 수행할 수 없어야 한다. 연구자가 fixture를 준비할 때만 Git에서 제외된 RCON 비밀번호와 `docker compose exec` 기반 host harness를 사용하며, RCON port는 host network에 publish하지 않는다.

기존 E0의 OP bot·hard reset 절차는 과거 tag/profile의 재현 기록으로만 남는다. Modernized Python bridge는 soft reset을 기본값으로 사용하고 world state injection을 명시적으로 거부한다. `/pause`도 기본 no-op이며 명시적 legacy adapter에서만 호출한다.

### 4. 자동검사 결과와 아직 주장하지 않는 것

```text
PASS spatial primitives keep the public Vec3 contract
PASS findSuitablePosition preserves water as a public-code target
PASS equipArmor preserves gold before chainmail
PASS killAnimal delegates target, combat and drop ownership once
PASS exploration seed 42 produces a repeatable non-constant sequence
PASS modernized execution profile contains no bot operator
6/6 primitive policy fixtures passed
```

Offline 결과 뒤 같은 날 modernized server를 실제 재기동해 권한 경계도 확인했다. 첫 RCON 호출은 server가 listener를 열기 1초 전에 도착해 connection refused가 발생했으며, server health 확인 뒤 재실행하면 정상 동작했다. 이 startup race를 반복하지 않도록 host harness는 connection refused에 한해서 1초 간격·최대 10회 재시도한다.

```text
Minecraft: healthy, RCON running on 0.0.0.0:25575
host prepare-player: inventory 3개 제거, player kill/respawn 성공
deop bot: Nothing changed. The player is not an operator
/health: connected=true, position_finite=true, inventory={}
/health: exploration_seed=42, exploration_rng_state=42
/health: operator_commands_enabled=false
agent /gamemode creative: Server commands are restricted to the host-admin RCON harness
RCON playerGameType after denial: 0 (survival)
```

따라서 server-level non-OP, host-only 관리자 경로, agent command 거부와 seed 42 초기 상태까지 online으로 통과했다. `killMob`의 combat plugin 부재 등 기존 감사에서 명백한 오류로 분류한 항목은 아직 수정하지 않았고, `GoalBlock` 판단은 합의한 순서대로 모든 나머지 문제 뒤로 미뤘다.

이번 실행의 `runtime/minecraft/mods`에는 과거 legacy pause JAR 4종이 남아 있어 server가 이를 함께 load했다. 권한 검증 경로는 `/health`, soft `/start`, `/step`과 RCON만 사용해 `/pause`를 호출하지 않았지만, 이 결과를 “mod-free 재검증”으로 확대하지 않는다. Bridge에서는 `physicTick` deprecated-event 경고도 한 번 관찰됐다. 현재 project source는 이미 `physicsTick`을 사용하므로 dependency 내부 발생 여부를 나머지 executor 경고 감사에서 추적한다. 두 관찰 모두 이번 non-OP·seed 판정을 바꾸지는 않았다.

정적 검색 결과 `odyssey/test_env/*`, `givePlacedItemBack`과 compositional `placeMinecartOnRail`에는 여전히 bot이 직접 `/tp`, `/fill`, `/give`, `/summon` 등을 호출하는 과거 경로가 있다. Modernized profile에서는 이 코드가 관리자 권한을 얻는 대신 명시적으로 거부된다. Test environment 준비 명령은 host harness로 옮기고, 논문 기능인 item 회수·minecart 배치는 일반 Mineflayer 동작으로 바꾸거나 별도 controlled fixture로 분류해야 한다. 이 후속 migration은 권한 경계를 무력화하지 않고 나머지 명백 오류와 함께 처리한다.

### 5. 근거 파일

- [Primitive policy offline fixture](../../../MineSkynet-odyssey/Odyssey/scripts/primitive_policy_offline.js)
- [Primitive 40 working manifest](../manifest/odyssey_primitive_40.json)
- [Host-only RCON harness](../../../MineSkynet-odyssey/Odyssey/scripts/host_admin_rcon.py)
- [Modern server operator profile](../../../MineSkynet-odyssey/Odyssey/server-profile/modernized/ops.json)
- [실행·검증 절차](../README.md#32-터미널-1-minecraft-서버-실행)

---

## 2026-09-09 — 이번 주 연구 목표: MineSkynet의 개선을 어떻게 입증할 것인가?

이번 주 계획의 상위 목표는 “어떻게 하면 MineSkynet이 기존 방법보다 개선되었다고 입증할 것인가?”에 답할 준비를 하는 것이다. 이는 블루프린트의 기존 연구 질문을 대체하는 문장이 아니다. 이를 위해 라우팅 관련 연구에서 문제·방법·평가 기준을 조사하고, MineSkynet의 세부 가설과 이를 검증할 실험을 구체화한다. 이번 주는 연구자의 회복과 작업 여건을 고려해 아래 두 목표에 집중한다. 아래 항목은 계획이며 조사·실험 완료를 뜻하지 않는다.

기존 benchmark와 실험 방법이 연구 질문을 평가할 수 있으면 이를 활용한다. 기존 연구가 답하지 못하는 MineSkynet의 독창적인 부분이 확인되고 기존 평가로 이를 측정하기 어렵다면, 그 공백을 검증하는 새 실험이나 benchmark를 설계한다. 독창성의 존재와 새 benchmark의 필요성 모두 조사 결과를 바탕으로 판단한다.

### 1. 라우팅 관련 연구 조사

기존 연구가 무엇을 개선했고 어떻게 입증했는지 파악해, MineSkynet의 비교 기준과 기여 후보를 찾는다.

#### 1.1. 관련 연구와 조사 범위 선정

- [~] 동료심사를 통과한 관련 논문 약 3편을 선정한다. VillagerAgent는 연구자가 선정하고 랩미팅에서 리뷰했다. 나머지는 Minecraft 작업 할당·라우팅부터 탐색하고, 직접 관련 연구가 부족하면 다중 에이전트 작업 할당과 LLM·에이전트 라우팅으로 범위를 넓혀 적용 근거를 기록한다.
- [ ] 각 연구의 문제, 할당 대상·단위, 선택 방식과 피드백 사용 방식을 정리한다. 질문 하나, subgoal 하나, 행동 구간 중 어느 단위인지 구분하고 in-context 학습의 역할도 확인한다.

#### 1.2. 개선을 입증한 근거 비교

- [ ] 기존 연구가 어떤 baseline, 과제·benchmark, 지표와 자원 예산으로 개선을 입증했는지 비교한다.
- [ ] 결과가 성립하는 조건과 한계를 정리하고, MineSkynet에 재사용 가능한 방법·평가 기준과 적용하기 어려운 부분을 구분한다.

#### 1.3. MineSkynet의 기여 후보 도출

- [ ] 기존 연구 질문 아래에서 기존 연구가 답한 부분과 남은 부분을 구분해 세부 질문·가설 후보를 작성한다. 차별점은 조사 근거와 함께 기록하고, 단순한 Minecraft 적용 차이인지 새로운 문제·방법상의 기여인지 검토한다.
- [ ] 각 후보에 대해 제안 방법과 대안을 적고, 라우팅이 필요한 이유를 설명한다. Planner와 실행 node의 물리적 분리라는 잠정 전제를 유지하면서 작업 할당 방법을 비교한다.

산출물은 **선행연구 비교표와 근거가 연결된 기여 후보**다. “기존 연구는 무엇을 입증했고, MineSkynet은 무엇을 추가로 확인하려는가?”에 답할 수 있으면 이 목표의 초안을 완료한 것으로 본다.

### 2. 실험/벤치마크 설계

첫 번째 목표에서 도출한 기여 후보를 측정 가능한 가설로 바꾸고, 어떤 결과가 개선을 지지하거나 반박하는지 정한다.

#### 2.1. 개선의 의미와 검증 가설 정의

- [ ] “어떤 조건에서, 어떤 방법보다, 무엇이 개선되는가?”를 한 문장으로 작성한다. 목표 달성률, 완료 시간, 고정 시간 내 목표 자원 확보량 등에서 연구 질문에 맞는 주 지표를 선택한다.
- [ ] 가설을 드러내는 최소 과제와 성공·실패 조건을 정의한다. 자원 확보나 prerequisite가 있는 tech tree 과제는 후보이며, 다양성보다 연구 질문과의 적합성을 우선한다.

#### 2.2. 기존 평가의 활용과 새 평가의 필요성 판단

- [ ] 선행연구의 benchmark·실험 절차로 가설을 검증할 수 있는지 확인하고, 그대로 활용할 부분과 수정이 필요한 부분을 기록한다.
- [ ] 기존 평가로 측정하기 어려운 독창적인 질문이 남는 경우, 누락된 조건과 그 이유를 명시해 새 실험 또는 benchmark의 최소 범위를 설계한다. 새로운 평가를 도입하더라도 기존 방법과 비교 가능한 기준을 마련한다.

#### 2.3. 공정한 비교와 측정 절차 구체화

- [ ] 고정 역할 분담, 단순 규칙 할당 등 적절한 baseline을 정하고, 제안 요소를 제외한 비교로 그 요소의 효과를 확인할 필요가 있는지 검토한다.
- [ ] 에이전트 수, 모델, 시작 자원, 시간·추론 예산과 world 조건 등 통제할 조건을 정한다. 주 지표와 함께 중복 작업, 재할당 횟수, 추론 비용 등 필요한 보조 지표를 선정한다.
- [ ] 반복 실행과 world seed·과제 변형의 구성, 개발용·평가용 조건 분리, 결과 변동성의 보고 방식을 초안에 포함한다.

#### 2.4. 목표에서 역산한 최소 구현과 예비실험 계획

- [ ] 실험에 필요한 최소 skill·관측 기능과 선행조건을 도출하고, 각 구현·디버깅 항목이 어떤 실험을 가능하게 하는지 연결한다.
- [ ] 실제 실행으로 확인해야 할 primitive 작동, 에이전트 간 간섭, subgoal 이해와 측정 가능성을 예비실험 항목으로 정한다. 예비실험으로 과제와 지표를 다듬은 뒤 본실험 조건을 고정한다.
- [ ] 연구 질문 → 가설 → 비교 방법 → 과제·지표 → 필요한 구현을 한 장의 연구 대시보드로 연결한다.

산출물은 **최소 실험설계 초안과 연구 대시보드**다. 다음 랩미팅에서 “어떤 개선을 어떤 비교로 확인하며, 기존 평가를 활용할지 새 평가가 필요한지, 실행 전에 무엇을 준비해야 하는지”를 설명하는 것이 이번 주 완료 기준이다. 최종 방법과 benchmark는 선행연구 조사 및 연구자 판단을 거쳐 확정하며, 현대화 작업의 우선순위도 이 실험의 필요에 맞춰 정한다.

---

## 2026-09-09 — 실험설계 논의: 물리적 분리와 경험 기반 개선의 두 축

### 1. 합의한 방향과 선행연구의 역할

MineSkynet의 개선을 입증하기 위해 기존 연구의 평가 방식을 조사하고, 기존 평가가 다루기 어려운 독창적인 질문이 확인될 때 새 실험·benchmark를 설계한다. VillagerAgent는 연구자가 이미 랩미팅에서 리뷰한 선정 논문이다. “축적된 skill을 고려한 작업 할당이 현재 상태만 고려한 할당보다 성과를 개선하는가?”는 열린 후보로 두고 다른 연구의 실험설계와 비교한 뒤 판단한다.

Lifelong in-context 구상은 성공·실패와 당시 조건을 축적하고, 이를 skill 코드·프롬프트 수정과 이후 행동에 활용하는 지속적인 피드백 순환을 포함한다. Skill retrieval만으로 범위를 한정하지 않는다. Filtering Learning Histories는 경험 context에 따른 의사결정 적응의 근거로 참조하되, 논문의 사전학습 데이터 선별(LHF)과 실행 중 기억·skill 갱신은 구분한다.

### 2. 잠정적인 시스템 전제

Planner와 edge 실행 node는 논리적으로뿐 아니라 서로 다른 물리 호스트에 배치하는 것을 전제로 구상한다. Docker는 각 호스트의 환경 격리·배포 수단으로 검토한다. 한 호스트의 여러 컨테이너는 사전 기능검증에 사용할 수 있으나 물리적 분산 평가와 구분한다.

Planner·실행 기능을 한쪽으로 통합하는 의미의 cloud-only/edge-only는 기본 비교군에서 제외한다. 주 비교는 물리 배치를 유지하면서 할당과 경험 활용 방식을 바꾸는 방향이다. 구체적인 노드 수·장치·모델 조합은 아직 정하지 않았다.

### 3. 구분해 평가할 두 개선 효과

| 개선 축 | 의미 |
| --- | --- |
| 코드·스킬 개선 | 내부 절차를 수정해 같은 skill의 실행 안정성·효율을 개선한다. 특정 task에서 확인한 효과가 다른 task로 이어지는지는 별도 검증한다. |
| 의사결정 개선 | 현재 관측과 누적 피드백을 활용해 skill 선택·순서·작업 할당을 개선한다. |

Observation space 자체의 확장과 기존 관측·이력을 활용한 판단 개선을 구분한다. 프롬프트 수정도 코드 생성에 영향을 주는지, 선택·할당에 영향을 주는지에 따라 분류한다. 전체 시스템의 성능 향상만으로 ICRL의 효과를 입증했다고 보지 않고, 이력 활용의 기여를 비교한다.

코드·스킬 갱신 허용 여부와 실행 의사결정에 누적 피드백을 제공하는지 여부를 교차한 네 조건을 실험 후보로 논의했다. 스킬 수정 과정에는 피드백을 사용하되 실행 시 선택에 제공하는 이력과 분리한다. 이 비교로 두 축의 개별 효과와 결합 효과를 확인할 수 있는지 검토하며, 아직 최종 protocol로 확정하지 않는다.

### 4. 예비실험과 남은 선택

목표·지표에서 필요한 최소 skill과 관측 기능을 역산하고, 실제 작동·에이전트 간 간섭·과제 난이도·측정 가능성은 예비실험으로 확인한다. 본실험 전에 조건을 고정하고 개발용·평가용 seed와 과제 변형을 분리하는 방향으로 설계한다.

기존 연구 질문은 유지한다. 세부 가설, 할당·피드백 단위, 기억·수정 정책, task·benchmark, baseline, 주 지표, 구체적인 노드 배치와 반복 규모는 미정이다. 다중 agent orchestration과 lifelong in-context의 필요성은 연구자가 명시했으며, 그 구현·평가 방식이 검토 대상이다. 이번 정리는 설계 합의이며 새로운 실험을 실행하거나 개선을 입증한 결과는 아니다.

### 5. 문서 반영

[블루프린트 §7 실험설계](./MineSkynet_blueprint.md#7-실험-설계)를 잠정 전제와 실험 후보 중심으로 재작성했다. 연관된 연구 질문·가설, 물리 배치, 능동 skill 갱신 범위와 성공 판정의 충돌 문장도 함께 정리했다. 세부 비교 조건과 통제 항목은 블루프린트에서 관리한다.

연구자의 후속 지적에 따라 임의 교체했던 연구 질문을 원문으로 복원했다. 주 비교는 다중 agent 환경에서 방법론 간 비교이며, 단일·다중 agent 비교는 보조 후보로 둔다. 기존 연구 질문과 lifelong 구상을 미정·선택 사항으로 축소한 표현, code repair 담당을 특정 계층으로 확정한 표현도 바로잡았다. 이번 주의 “개선 입증” 목표는 기존 연구 질문을 구체적인 실험으로 연결하기 위한 목표이며 연구 질문 변경을 승인한 것으로 해석하지 않는다.

---

## 2026-09-09 — Minecraft 라우팅 benchmark 후보 조사와 현재 합의

### 1. 조사 목적과 범위

MineSkynet만을 위한 새 benchmark를 먼저 만들지 않고, Minecraft 안에서 다중 agent 작업 할당을 직접 평가한 기존 과제와 판정기를 우선 탐색했다. 일반적인 agent-routing benchmark를 변형하는 방안은 직접 적용할 수 있는 Minecraft 연구가 부족하거나 연구 질문보다 지나치게 좁을 때의 후순위 대안으로 남겼다.

이번 조사는 최종 benchmark 확정이나 실험 완료가 아니다. **채용 가능한 주 benchmark 후보와 Discussion에서만 다룰 방법론을 구분한 중간 선정 결과**다.

### 2. 주 benchmark 후보

| 연구 | 현재 지위 | 가져올 핵심 | 그대로 채용하지 않는 범위 |
| --- | --- | --- | --- |
| VillagerAgent / VillagerBench | 기본 benchmark | 건축 협업, farm-to-table 요리, escape room의 task·판정 방식과 DAG 기반 작업 할당 baseline | 현재 공개 구현의 모든 orchestration 방법을 MineSkynet 최종 방법으로 확정하지 않음 |
| MineCollab / MINDCraft | 특수 조건 후보 | agent별 자원·recipe·도구 능력을 나누어 단일 agent가 전체 과제를 해결할 수 없게 하는 필수 협업 조건, 요리·제작·건축 validator | 자연어 통신 능력 자체를 MineSkynet의 주 연구 문제로 확대하지 않음 |
| TickingCollabBench | 특수 조건 후보 | agent capability 차이, 실제 시간이 흐르는 실행, 동적 목표와 failure risk, 중앙·분산·oracle 비교 및 추론 지연·통신비용 기록 | 재난·보스전과 2~8 agent 전체 구성을 초기 benchmark에 일괄 도입하지 않음 |

VillagerBench를 공통 평가 기반으로 유지하고, MineCollab에서는 **필수적인 자원·skill 비대칭**, TickingCollabBench에서는 **이질성과 실시간 제약을 분리해 선택적으로 주입**하는 방향에 합의했다. 두 연구의 benchmark를 통째로 결합하거나 task 수를 먼저 늘리지 않는다.

### 3. CausalMACE의 판정 변경

CausalMACE는 별도의 더 큰 다중-agent benchmark를 제시한 연구가 아니다. VillagerBench의 건축·요리·escape room 전체와 기존 지표를 재사용하고, 여기에 단일-agent 자원 획득 실험을 별도로 추가했다. 따라서 “VillagerBench가 CausalMACE benchmark의 부분집합”이라기보다 **CausalMACE가 VillagerBench를 평가 기반으로 계승했다**고 구분한다.

CausalMACE는 VillagerAgent의 전역 계획 이탈과 잘못된 subtask dependency를 문제로 제기하고, causal task graph와 실행 경로별 busy rate를 이용해 같은 VillagerBench에서 완료율과 효율을 개선했다. 이 문제제기와 ablation은 MineSkynet의 dependency 관리와 workload-aware routing을 설명하는 데 유용하다.

그러나 현재 확인된 범위에서는 다음 이유로 주 benchmark 후보에서 제외하고 **Discussion 및 강한 비교 방법 후보**로 지위를 변경했다.

- 공식 공개 구현을 확인하지 못해 재현·채용 가능성이 VillagerAgent보다 낮다.
- Worker의 busy rate는 경로 혼잡도와 배정 agent 수를 반영하지만 actor별 skill 성공률, 예상 실행시간, 물리 장치 비용이나 누적 실행 이력을 직접 모델링하지 않는다.
- Causal refinement가 LLM 추론 능력에 크게 의존해 작은 model의 적용성이 낮다는 한계를 논문도 명시한다.
- 다중-agent 과제와 판정기는 VillagerBench를 재사용하므로 독립 benchmark 후보로 중복 계산하지 않는다.

VillagerAgent는 공개 코드와 benchmark 원출처이자 현재 상태 기반 DAG 할당의 baseline으로 유지한다. CausalMACE는 이를 대체하는 상위호환으로 취급하지 않고, 전역 dependency 정제와 부하분산에서 이후 제안된 개선으로 인용한다.

### 4. 현재 benchmark 구성 방향

잠정적인 구성 원칙은 다음과 같다.

1. VillagerBench의 과제 중 연구 질문을 드러내는 최소 과제를 선택하고 기존 성공·부분 달성 판정을 출발점으로 삼는다.
2. MineCollab을 참고해 필요한 재료·recipe·skill을 actor 사이에 비대칭적으로 나누고, 협업이 단순한 동일 agent 수 증가가 아니라 과제 성공의 필요조건이 되게 한다.
3. TickingCollabBench를 참고해 capability heterogeneity와 synchronous/asynchronous 실행을 구분한다. 동적 spawn, 짧은 deadline과 failure event는 기본 과제의 측정 가능성을 확인한 뒤 stress condition으로 검토한다.
4. 게임 속 도구·이동속도 차이와 실제 물리 컴퓨터의 model 성능·지연·memory·energy 차이를 같은 변수로 취급하지 않는다. 후자는 MineSkynet이 별도로 측정하고 배정에 사용할 물리 actor capability다.
5. 주 비교에서는 planner와 실행 node의 물리적 분리를 유지하고, 고정·무작위 할당, 현재 상태 기반 할당, 측정 capability 기반 할당과 누적 피드백을 활용한 할당 중 연구 질문에 필요한 조건을 선정한다.

초기 실험 후보는 VillagerBench의 건축 또는 요리처럼 prerequisite와 병렬 작업을 함께 포함하는 과제다. 주 지표 후보는 완료율·완료시간·고정 시간 내 산출량이며, 중복 작업, idle time, retry·timeout·재할당, 통신·추론비용과 energy를 보조 지표로 검토한다. 아직 과제 하나, 주 지표와 비교 조건을 최종 확정하지 않았다.

### 5. 조사 후 배제한 후보

| 연구 | 배제 이유 |
| --- | --- |
| TeamCraft | 중앙·분산 방식, agent 수와 inventory 변화, 중복 행동 지표는 유용하지만 연구 중심이 멀티모달 관측과 미관측 scene·goal·agent 수에 대한 일반화여서 현재 물리 actor 작업 할당 질문과 거리가 있다. |
| Gated Coordination | local recovery와 public communication 사이의 escalation 및 통신 효율을 주로 다룬다. 실행 중 재시도·재배정의 보조 지표로는 참고할 수 있지만 초기 subtask-to-actor 할당 benchmark와는 범위가 다르다. |

두 연구는 현재 주 benchmark와 관련논문 선정 후보에서 제외한다. 이후 확정된 가설에 멀티모달 일반화나 통신 escalation이 필요해질 때만 다시 검토한다.

### 6. 출판 상태와 남은 확인

VillagerAgent는 ACL Findings 2024 논문과 공개 구현을 갖는다. MineCollab은 arXiv에서 *Collaborating Action by Action: A Multi-agent LLM Framework for Embodied Reasoning*이라는 제목을 사용하며, NeurIPS 2025 LAW workshop의 *Blocks, Bots, and Bottlenecks: Studying Real-time and Adaptive Multi-Agent LLM Collaboration*은 같은 저자·platform·benchmark와 핵심 실험을 공유하는 제목 변경 버전이므로 별도 논문으로 세지 않는다. 공개 platform·benchmark가 있으며, TickingCollabBench는 2026년 공개된 preprint다. 따라서 **benchmark 채용 가능성 판단과 동료심사를 통과한 관련논문 약 3편의 선정은 같은 판정이 아니다.** TickingCollabBench는 문제 적합성이 높더라도 출판 상태를 명시해 사용하고, 관련논문 선정 요건은 별도로 점검한다.

다음 조사에서는 세 주 후보에 대해 task 수·초기 자원·agent 수·시간 제한·성공 판정·반복 seed·공개 코드 실행조건을 같은 표로 대조한다. 그 뒤 VillagerBench 과제를 그대로 사용할 부분과 MineCollab·TickingCollabBench에서 추가할 최소 조건을 정하고, 선택한 조건이 MineSkynet의 어떤 가설을 검증하는지 연결한다.

### 7. 논문 및 공개 자료

- [VillagerAgent 논문](https://aclanthology.org/2024.findings-acl.964/)
- [VillagerAgent 공개 구현](https://github.com/cnsdqd-dyb/VillagerAgent-Minecraft-multiagent-framework)
- [MineCollab / MINDCraft 논문 — Collaborating Action by Action](https://arxiv.org/abs/2504.17950)
- [같은 연구의 NeurIPS 2025 LAW workshop 제목 — Blocks, Bots, and Bottlenecks](https://neurips.cc/virtual/2025/137194)
- [TickingCollabBench 논문](https://arxiv.org/abs/2606.15684)
- [CausalMACE 논문](https://aclanthology.org/2025.findings-emnlp.777/)

---

## 2026-09-14 — 주력 선행연구 재설정과 Odyssey actor service 분리 방향

### 1. 문제상황과 선행연구의 역할 재설정

MineSkynet은 여러 agent의 과제를 분해하고 실행자를 배정하며 진행 상태를 공유하는 **다중-agent orchestration**을 주된 문제로 다룬다. 이 기준에서는 단일 agent의 장기 탐색과 skill 축적을 중심으로 한 Voyager보다, task decomposer·agent controller·state manager를 갖추고 VillagerBench에서 협업을 평가한 **VillagerAgent가 주력 선행연구와 orchestration baseline에 더 직접적으로 부합한다.**

따라서 VillagerAgent의 세 역할은 MineSkynet control plane의 기준으로 유지한다.

- `task decomposer`: 전역 목표를 dependency가 있는 subtask로 분해한다.
- `agent controller`: subtask를 actor에 배정하고 실행을 조정한다.
- `state manager`: agent와 world의 공유 상태를 관리하고 완료 여부 및 재계획에 필요한 정보를 제공한다.

Odyssey 전체 controller를 이 구조에 중첩하면 PlannerAgent·CriticAgent·CommentAgent와 전역 상태 처리가 VillagerAgent의 책임을 침해하고, 어느 계층의 판단이 성능을 만들었는지 분리하기 어려워진다. 이에 따라 Odyssey는 주력 orchestration 선행연구가 아니라 **Minecraft 실행 actor와 축적된 skill을 검색·재사용하는 보조 기반**으로 역할을 제한한다.

여기서 lifelong in-context 요소는 성공·실패 경험과 skill 자산을 이후 실행에 재사용하는 방향을 뜻한다. 다만 현재 공개 Odyssey 코드에서 직접 확인된 것은 고정 skill library의 semantic retrieval과 실행 경로이며, 새 skill의 생성·검증·수정·누적을 완결된 online lifecycle로 간주하지 않는다. 능동 skill lifecycle은 Voyager 계보의 아이디어를 별도 profile로 보존하고, MineSkynet의 orchestration 개선과 혼합해 주장하지 않는다.

### 2. 제안 아키텍처와 책임 경계

잠정 아키텍처는 **중앙 VillagerAgent control plane + 교체 가능한 Odyssey-derived actor service**다.

```text
VillagerAgent control plane
  task decomposition · dependency 관리 · actor 배정
  shared state · 전역 성공 판정 · retry/reallocation
                         |
              subtask 또는 skill request
                         v
Odyssey-derived actor service
  local skill catalog/retrieval · 선택 정책 · Mineflayer 실행
  관측 event · 실행 오류 · latency · local resource 상태 반환
                         |
                         v
                  Minecraft server
```

기본 contract는 control plane이 `actor_id`, `subtask` 또는 `skill_id`, 인자, timeout과 허용 skill을 전달하고, actor가 실행 event·오류·소요시간·종료 상태를 반환하는 형태로 둔다. Actor는 자신의 로컬 실행 성공 여부를 보고할 수 있지만 전역 subtask 완료, dependency 해소와 재계획을 최종 판정하지 않는다.

초기 통합에서는 VillagerAgent가 `skill_id + arguments`까지 정해 보내는 직접 실행 방식을 우선 검토한다. 이후 이기종 의사결정의 비교가 필요할 때만 actor 내부 selector를 rule base, decision tree, semantic retrieval 또는 sLLM 정책으로 교체한다. Docker는 이러한 actor별 실행환경과 dependency를 격리하는 배포 수단이며 그 자체를 연구 기여로 간주하지 않는다. 실제 물리 actor 수와 장치 조합은 가용 장비에 맞춰 열어 두고, 세 대를 필수 전제로 고정하지 않는다.

### 3. Odyssey에서 분리 가능한 기능

현재 코드에는 완성된 `ActorService` 클래스가 따로 존재하지 않지만 다음 기능 경계는 논리적·기능적으로 분리할 수 있다.

| 모듈 경계 | 보존할 기능 | 기본 actor 포함 여부 |
| --- | --- | --- |
| Mineflayer execution bridge | Minecraft 접속, `/start`·`/step`·health, 이동·채집·제작 등 JS skill 실행 | 필수 |
| Skill catalog | 검증된 primitive/compositional skill의 ID·entrypoint·code·capability 관리 | 필수 |
| Skill selector | 전달된 subtask에서 실행할 skill 선택 | 선택; direct ID, rule, decision tree, retrieval, sLLM로 교체 가능 |
| Semantic retriever | embedding과 vector search로 top-k skill 검색 | 선택 |
| Skill lifecycle | 새 skill 생성·설명·검증·versioning·재사용 | 별도 lifelong profile |
| Odyssey planner/critic/comment | 목표 분해, 전역 성공 판정과 feedback 생성 | actor에서 제외 |
| Odyssey `Multi-Agent/` controller | 자체 task checker·memory·coordination | VillagerAgent와 충돌하므로 제외 |

기존 `run_raw_skill`과 Mineflayer `/step` 경로는 planner·critic 없이 실행이 가능하다는 근거다. 그러나 chat 문자열만 반환하는 raw helper를 그대로 service contract로 삼지 않고, 관측 event·오류 유형·latency·request ID를 구조화해 반환해야 한다.

### 4. 현재 의존성 문제

Odyssey의 현재 Python packaging은 실행, semantic retrieval, 외부 model SDK와 Minecraft launcher를 하나의 기본 `requirements.txt`에 묶고 `extras`를 제공하지 않는다. 그 결과 단순 실행 actor에도 사용하지 않는 대형 의존성 연결고리가 생긴다.

- `SkillManager`는 생성 시 Hugging Face embedding과 Chroma vector DB를 항상 초기화하므로, 고정 catalog만 필요한 actor에도 PyTorch·Transformers·Sentence Transformers·Chroma·ONNX Runtime과 그 하위 dependency가 따라온다.
- `ActionAgent`는 LangChain message class를 단순 메시지 container로 사용하고, Python `javascript` bridge를 통해 Babel AST parser를 호출한다. `@babel/core`와 `@babel/generator`는 실제 사용되지만 상위 Node manifest에 직접 선언되지 않았다.
- `VoyagerEnv`는 Gym 학습 interface를 실질적으로 사용하지 않으면서 `gymnasium.Env`를 상속한다.
- `psutil`은 주로 subprocess 시작·상태·종료에, `coloredlogs`는 출력 형식에 사용된다.
- `minecraft_launcher_lib`는 Azure login으로 로컬 Minecraft instance를 띄우는 경로 때문에 import되며, 공용 server에 접속하는 actor에는 필요하지 않다.
- `openai`, `tiktoken`, `chardet`, `cchardet`, `tqdm`은 현재 조사한 Odyssey Python source에서 직접 사용을 확인하지 못한 제거 후보다. 삭제 전 entrypoint와 보조 script까지 다시 확인한다.
- Node bridge의 Mineflayer·minecraft-data·pathfinder·tool·collectblock은 실행 핵심이지만, PVP와 Hawkeye는 combat을 사용하지 않는 profile에서는 선택 dependency로 둘 수 있다.
- 현재 Docker Compose는 Java 17/Fabric Minecraft server만 정의하며 actor image, ARM64 profile과 actor별 capability 선언은 아직 없다.

이 구조는 Raspberry Pi 등 제한된 actor에도 retrieval과 model SDK를 강제로 설치하게 하고, orchestration 실험과 dependency 차이의 효과를 혼동시킬 수 있다.

### 5. 해결 방향

의존성 경량화는 선행연구 기능을 일괄 삭제하거나 신뢰받는 retrieval 구현을 이유 없이 재작성하는 작업이 아니다. **사용 빈도가 낮고 연구상 핵심이 아닌 편의 계층은 native code로 대체하고, 핵심 기능은 선택 profile로 격리**한다.

1. `actor-core`에는 Node/Mineflayer bridge, 작은 Python 또는 HTTP adapter와 정적 skill catalog만 둔다. 가능하면 VillagerAgent가 Node HTTP API를 직접 호출해 Python wrapper도 선택 사항으로 만든다.
2. `gymnasium.Env`는 일반 `ActorRuntime` class와 명시적 request/response type으로 대체한다. LangChain message object는 `dict` 또는 작은 `dataclass`로 바꾼다.
3. 런타임 Babel parsing 대신 build-time에 검증한 skill manifest에 `skill_id`, file, entrypoint, argument schema, capability와 timeout을 기록한다. 이를 통해 Python `javascript`와 Babel 연결고리 및 임의 code 실행 범위를 줄인다.
4. `psutil`은 표준 `subprocess.Popen`과 process-group 정리로, `coloredlogs`는 표준 `logging`으로 대체할 수 있다. 공용 server profile에서는 `minecraft_launcher_lib` 경로를 lazy import하거나 server-launcher package로 분리한다.
5. `SkillManager`를 `SkillCatalog`, `SkillRetriever`, `SkillLifecycle`, `SkillExecutor`로 나눈다. 기본 actor는 catalog와 executor만 사용한다.
6. 작은 고정 skill 집합은 사전 계산한 vector와 단순 L2/cosine top-k로 Chroma를 대체할 수 있다. 다만 semantic retrieval 자체를 연구 조건으로 평가하거나 catalog 규모·동적 갱신이 외부 구현을 정당화할 때는 검증된 Chroma/Sentence Transformer stack을 별도 `semantic-retrieval` profile로 유지한다.
7. sLLM selector는 model runtime을 actor package에 합치지 않고 별도 service의 HTTP/JSON contract로 호출한다. 비학습 비교군은 rule base와 decision tree로 구현해 동일한 skill manifest와 executor를 공유한다.
8. Node 실행 계층은 lockfile과 현재 버전 pin을 유지한다. TypeScript로 작성된 bundled collectblock은 build stage에서 컴파일해 runtime image에서 compiler와 type package를 제외하고, combat은 별도 extra로 분리한다.

권장 배포 profile은 `actor-core`, `actor-selector`, `semantic-retrieval`, `skill-learning`, `minecraft-server`다. 이 분리는 VillagerAgent의 orchestration 책임을 코드와 dependency 수준에서 보존하면서, MineSkynet이 비교하려는 물리 actor의 연산 능력·정책·지연 차이를 명확하게 노출한다.

### 6. 현재 판정과 남은 결정

이번 합의는 VillagerAgent를 주력 선행연구로, Odyssey를 actor 실행 및 lifelong in-context 요소의 보조 연구로 재배치한다. 구현 착수 전에는 VillagerAgent가 skill ID까지 선택할지 subtask만 전달하고 actor가 선택할지, semantic retrieval을 중앙화할지 actor별 실험 조건으로 둘지 결정해야 한다. 이 선택은 MineSkynet이 검증할 가설과 benchmark 조건을 기준으로 확정한다.

현재 단계에서는 Odyssey 전체를 VillagerAgent 안에 넣거나 native 재구현 범위를 Mineflayer 핵심까지 확대하지 않는다. 먼저 actor service contract와 dependency profile을 고정한 뒤, 각 profile이 보존하는 논문 기능과 제거한 편의 dependency를 회귀 fixture로 확인한다.

---

## 2026-09-23 — VillagerAgent 원본 실행 전 비파괴 점검

### 1. 현재 우선순위와 문서 기준

MineSkynet의 orchestration 기반으로 VillagerAgent를 채택할 수 있는지 판단하려면 새로운 통신 방식이나 이기종 routing을 먼저 구현하기보다, **공개 코드가 현재 환경에서 실제로 실행되고 VillagerBench의 결과와 비용을 산출할 수 있는지 확인하는 것이 우선**이다. 자연어 소통과 구조화 protocol 중 무엇을 연구할지, 물리 장치 이질성을 독립 연구 질문으로 얼마나 확장할지는 원본 실행 경로를 확인한 뒤 결정한다.

연구자 간 진행상황·판단·실험 근거를 공유하는 기준 인터페이스는 별도 문서를 새로 만들지 않고 현재 `/home/pluto2479/Documents/MineSkynet/research`를 그대로 사용한다. 누적 사실과 당시 판정은 이 리포트 로그에 기록하고, 현재 목표와 완료 조건은 마일스톤, 랩미팅 발표용 선별 내용은 `labmeeting_temp.md`에서 관리한다. VillagerAgent 소스와 실행 산출물은 `/home/pluto2479/Documents/MineSkynet-villager-agent`에 격리한다.

### 2. 확인한 공개 실행 경로

README가 제시하는 최소 실행은 Minecraft 1.19.2 server를 먼저 실행한 뒤 `tiny_start.py`를 구동하는 방식이다. 이 경로는 한 명의 Mineflayer agent `Alice`, TaskManager·DataManager·GlobalController와 외부 LLM API를 함께 초기화한다. Bot 접속 뒤 server console에서 OP 권한을 부여하도록 안내돼 있다.

기본 LLM 설정은 DashScope의 OpenAI-compatible endpoint와 `qwen3-next-80b-a3b-instruct`이며, API key는 저장소 root의 `API_KEY_LIST`에서 읽는다. Python–Node 연결은 `javascript` package를 통해 Mineflayer, pathfinder, collectblock, PVP, Hawkeye, minecraft-data와 viewer 등을 load한다.

Batch benchmark는 `config.py`가 생성하는 configuration과 `start_with_config.py`를 사용한다. 후자는 construction·farming·puzzle·meta task에 따라 agent tool을 등록하고, TaskManager·DataManager·GlobalController를 초기화한 뒤 score와 action/token log를 수집하는 경로다. 원본 실행 확인 전에는 이 batch 경로보다 `tiny_start.py`의 단일-agent smoke test를 먼저 사용한다.

### 3. 현재 로컬 상태와 즉시 확인된 blocker

이번 점검에서는 package 설치, API 호출, Minecraft 접속과 source 수정 없이 파일·버전·port·import 존재 여부만 확인했다.

| 항목 | 확인 결과 | 판정 |
| --- | --- | --- |
| Python | system Python 3.14.4 | pinned legacy dependency와 바로 결합하지 않고 Python 3.10 격리환경 필요 |
| Node/npm | Node 20.13.1, npm 10.5.2 | 버전 존재만 확인; 실제 package 호환성은 미검증 |
| Python package | requirements의 주요 package가 현재 환경에 없음 | 별도 환경에 clean install 필요 |
| Node package | `node_modules`가 없고 `npm ls --depth=0`에서 11개 direct dependency가 모두 누락 | `npm install`과 `js_setup.py` import 검사 필요 |
| API credential | `API_KEY_LIST` 없음 | 연구자가 선택한 provider의 key와 외부 호출 승인 필요 |
| Minecraft server | localhost 25565 listener 없음 | Minecraft 1.19.2 server 준비 필요 |
| QuickStart config | `tiny_start.py`는 존재 | 최소 실행 entrypoint 후보 |
| Batch config | `base_agent_multi_test_config.json` 없음 | `config.py`로 생성 조건을 확인한 뒤 batch 실행 |
| Docker entrypoint | Dockerfile은 존재하지 않는 `run.py`를 실행 | 현재 Dockerfile을 재현 경로로 사용하지 않음 |

현재 requirements에는 LangChain 0.0.350, OpenAI 1.6.1, FlagEmbedding 1.1.3, Google·Zhipu·Mistral·DashScope adapter, Gymnasium, AutoGPTQ 등 실행 목적이 다른 dependency가 한 파일에 함께 선언돼 있다. 지금 단계에서는 이를 먼저 현대화하거나 제거하지 않고, 원본 기능 재현에 실제로 필요한 package와 실패 지점을 설치 과정에서 증거로 남긴다.

### 4. 최소 재현 순서와 완료 기준

실행 가능성 확인은 실패 원인을 한 단계씩 분리하기 위해 다음 순서로 진행한다.

1. Python 3.10 격리환경에서 requirements의 설치 가능 여부와 import를 확인한다.
2. Node dependency를 lock 상태와 함께 설치하고 `js_setup.py`가 모든 module을 load하는지 확인한다.
3. Minecraft 1.19.2 server를 준비하고 단일 Mineflayer bot의 접속·종료를 확인한다.
4. 외부 LLM 호출 전 TaskManager·DataManager·Controller 초기화에서 발생하는 source/runtime 오류를 확인한다.
5. 승인된 API credential로 `tiny_start.py`의 한 개 요청을 실행하고 실제 호출·token·latency·오류를 기록한다.
6. 대표 VillagerBench 과제 하나를 단일 configuration으로 실행해 completion score, action log와 token log가 함께 생성되는지 확인한다.
7. 단일 실행이 반복 가능할 때만 batch configuration과 agent 수 변화 실험으로 확장한다.

첫 완료 기준은 “VillagerAgent 전체 benchmark 재현”이 아니다. **한 개의 통제된 task가 시작·실행·종료되고, 실행 결과와 LLM 비용 근거가 남는 것**을 최소 재현 완료로 본다. 원본 코드의 결함이나 dependency 충돌이 발견되면 원본 실패와 호환성 patch 이후 결과를 구분한다.

### 5. API 비용 조사 범위

저렴하고 충분히 강한 API 후보는 단일 호출 가격만으로 선정하지 않는다. VillagerAgent는 decomposer, controller/data manager와 base agent가 여러 차례 LLM을 호출할 수 있으므로 다음을 episode 단위로 측정한다.

- component별 inference 횟수와 재시도 횟수
- agent 수에 따른 총 호출 증가
- 입력·출력 token과 wall-clock latency
- task 성공 1회당 총비용
- 같은 task에서 model tier별 completion과 비용

큰·중간·작은 model을 task 난이도에 따라 routing하는 질문은 원본 호출 구조와 비용을 확인한 뒤 최소 비교로 구체화한다. 물리 이기종 device 자체의 효과, model 정확도와 context 차이의 효과를 한 결과로 섞어 인과적으로 주장하지 않는다.

### 6. 근거 파일

- [VillagerAgent 실행 안내](../../../MineSkynet-villager-agent/README.md)
- [최소 QuickStart](../../../MineSkynet-villager-agent/tiny_start.py)
- [Batch 실행 경로](../../../MineSkynet-villager-agent/start_with_config.py)
- [Benchmark configuration 생성](../../../MineSkynet-villager-agent/config.py)
- [Python dependency 선언](../../../MineSkynet-villager-agent/requirements.txt)
- [Node dependency 선언](../../../MineSkynet-villager-agent/package.json)
- [현재 Dockerfile](../../../MineSkynet-villager-agent/Dockerfile)

---

## 2026-09-23 — VillagerAgent 외부환경 1–3단계 실행 결과

원본 source를 수정하지 않은 상태에서 Python·Node 실행환경과 Minecraft server 접속 기반을 준비했다. 이 단계는 **환경 준비 완료**이며 VillagerAgent bot, controller, LLM 호출 또는 benchmark 성공을 의미하지 않는다.

### 1. Python 3.10 환경

저장소 내부 `.venv`에 Python 3.10.20 Conda 환경을 생성하고 원본 `requirements.txt`를 그대로 설치했다. LangChain, scikit-learn, Python `javascript`, FlagEmbedding, OpenAI client, Flask, Gymnasium, DashScope, Torch와 Transformers를 포함한 주요 import가 통과했다.

원본 requirements가 `torch`, `transformers`, `optimum`, `auto-gptq` 등의 상한과 runtime profile을 고정하지 않아 2026-09-23 설치에서는 Torch 2.14.0+cu130과 CUDA 13 관련 package가 선택됐고 `.venv` 크기는 약 6.5GB가 됐다. 이는 최소 VillagerAgent 실행 요구가 확인된 결과가 아니라 원본 dependency 선언이 허용한 설치 결과다. LangChain이 요구한 `packaging==23.2`와 Conda 기본 `wheel==0.47.0`의 build-tool 충돌은 runtime package를 변경하지 않고 `wheel==0.45.1`로 맞췄으며, 이후 `pip check`는 `No broken requirements found`를 반환했다.

### 2. Node dependency

원본 저장소에는 lockfile이 없으므로 새 lockfile을 생성하지 않는 `npm install --no-package-lock`로 package를 설치했다. 247개 package가 설치됐고 `npm ls --depth=0` 및 `js_setup.py`의 Mineflayer 관련 module load가 통과했다.

다만 caret 범위 때문에 `mineflayer@^4.23.0`은 현재 `4.39.0`으로, `minecraft-data@^3.80.0`은 `3.117.0`으로 해석됐다. Mineflayer 4.39.0과 전이 dependency인 minecraft-protocol 1.68.0은 Node 22 이상을 요구하지만 현재 Node는 20.13.1이어서 engine warning이 발생했다. npm audit은 moderate 12건과 high 1건을 보고했다. `npm audit fix`나 임의 upgrade는 적용하지 않았다. 다음 bot 단계 전에는 원 논문 시기의 버전을 고정할지 Node 22에서 현재 해석 결과를 검증할지 결정해야 한다.

### 3. Minecraft 1.19.2 server

`itzg/minecraft-server:java17` image로 Vanilla 1.19.2 server를 `villageragent-mc-1.19.2` container에 실행했다. World와 server data는 Git에서 제외한 `MineSkynet-villager-agent/.runtime/minecraft`에 저장한다.

```text
container: villageragent-mc-1.19.2
image: itzg/minecraft-server:java17
Minecraft: Vanilla 1.19.2
memory: 2G
published port: 127.0.0.1:25565 -> 25565/tcp
online-mode: false
health: healthy
```

Server log의 `Done (15.378s)`와 `Starting minecraft server version 1.19.2`를 확인했고, host에서 `127.0.0.1:25565` TCP 연결도 통과했다. RCON은 container 내부에서 시작됐지만 host port로 publish하지 않았다. Offline mode는 로컬 재현을 위한 현재 실행조건이며 외부 network에 server port를 공개하지 않는다.

### 4. 다음 단계 진입 조건

1–3단계의 환경과 server는 준비됐지만 Node engine warning이 남아 있다. 다음 4–6단계에서는 먼저 단일 bot의 join·기본 명령·종료를 확인해 현재 Node dependency 조합의 실제 호환성을 판정한다. 그 결과를 얻기 전에는 benchmark나 Odyssey 이식을 진행하지 않는다. `tiny_start.py`의 LLM 요청은 bot 연결이 확인되고 API credential·호출 예산을 연구자가 승인한 뒤 실행한다.

---

## 2026-09-23 — 이기종 작업 할당과 scheduling·congestion의 연관성 조사 제안

현재 연구질문인 **“상이한 연산·메모리 능력을 가진 actor에 작업을 적절히 분배할 수 있는가?”**는 OS의 이기종 자원 scheduling 및 컴퓨터 network의 부하·congestion 제어 문제와 구조적으로 연결될 가능성이 있다. 장치별 처리능력과 메모리 한계를 고려한 배치, 작업 대기시간과 처리량, 특정 고성능 actor로의 요청 집중, queue 적체와 병목은 MineSkynet의 할당 정책과 평가 지표를 구체화할 때 무시하기 어려운 요소다.

다만 이 연관성은 아직 문헌 조사로 확인한 결론이 아니다. 현 단계에서는 범용 scheduler나 congestion-control algorithm 자체를 새로운 연구주제로 확장하지 않고, MineSkynet의 hardware-aware task allocation을 설명하고 비교 정책을 설계하기 위한 후보 이론으로만 둔다. 관련 연구가 실제 문제 설정·관측 변수·평가 지표에 유의미한 근거를 제공하는지는 후속 조사를 통해 판정한다.

이 조사에 앞서 VillagerAgent의 기존 할당 정책을 논문과 코드 양쪽에서 확인한다. 구체적으로 다음을 구분한다.

1. Task decomposer가 subtask에 요구 능력, 예상 비용 또는 우선순위를 표현하는가.
2. Global controller가 agent를 선택할 때 능력, 현재 부하, memory, 예상 실행시간 또는 과거 성공률을 사용하는가.
3. 실제 배정이 LLM의 자연어 판단, dependency graph의 순서, 고정·rule-based 정책 중 무엇으로 이루어지는가.
4. 실패·지연·queue 적체가 발생했을 때 retry와 reallocation을 수행하는가.
5. 논문이 설명한 정책과 공개 코드의 실제 실행 경로가 일치하는가.

우선 VillagerAgent의 현행 정책을 baseline으로 명확히 규정한 뒤, 그 정책이 사용하지 않는 hardware·load 정보를 식별한다. 이후에만 capability-aware 또는 hardware-aware 정책이 어떤 추가 정보를 사용하며 기존 정책보다 무엇을 개선하는지를 비교한다. 이때 model 정확도·context 차이와 물리 장치 자원 차이를 하나의 효과로 합쳐 인과적으로 주장하지 않는다.

---

## 2026-09-23 — 외부 LLM 공급 경로 통일안과 로컬 모델 대안

### 1. 연구상 목적과 중개 API 문제

VillagerAgent의 원본 실행과 이후 model-tier routing을 비교하려면 model 자체의 능력·비용·지연과 호출 인프라에서 발생한 변동을 구분할 수 있어야 한다. `api.chatanywhere.tech`와 같은 제3자 중개 API를 사용하면 요청·응답이 추가 사업자를 경유하고, 실제 model revision, data retention, rate limit, cache, retry와 장애 원인을 독립적으로 확인하기 어렵다. 따라서 관찰된 latency나 실패가 model, 공식 공급자, 중개자 중 어디서 발생했는지 분리하기 어려워지고 개인정보 처리와 실험 재현성의 근거도 약해진다.

중개 API가 데이터를 오용한다고 단정한 것은 아니다. 다만 공개적으로 확인 가능한 보안·보존 정책과 model provenance가 공식 공급자보다 제한적인 상황에서, 낮은 호출 단가만으로 본 실험 경로에 채택할 근거가 부족하다고 판정했다. 중개 API는 비민감 합성 prompt를 이용한 개발 편의용 smoke test에도 현재 기본값으로 두지 않는다.

### 2. 외부 API 통일 구상

외부 LLM 호출은 공식 Google Gemini API의 **유료 tier**로 통일하는 방향을 채택한다. 이는 단순히 공급자 수를 줄이는 조치가 아니라, 동일한 인증·과금·사용량 기록·장애 경로 아래에서 model tier의 차이를 비교하기 위한 통제다. Google의 공개 정책상 유료 Gemini API의 prompt와 response는 제품 개선에 사용되지 않지만, 무료 tier는 사용될 수 있으므로 개인정보·미공개 연구정보 보호를 이유로 공급자를 통일하면서 무료 tier를 기본 실험 경로로 쓰지는 않는다.

현재 외부 후보는 다음 두 개로 제한한다.

| 역할 | Model과 추론 설정 | 2026-09-23 표준 유료 가격(입력/출력, 1M token) | 현재 판정 |
| --- | --- | ---: | --- |
| 주력 외부 기준 | `gemini-3.8-flash`, `thinking_level=low` | `$0.75 / $3.75` | agentic planning·tool use를 포함한 VillagerAgent 재현 후보 |
| 저비용·하위 tier | `gemini-3.5-flash-lite`, `thinking_level=minimal` | `$0.30 / $2.50` | 단순 actor·고빈도 호출과 저성능 비교 후보 |

`gemini-3.8-flash`의 위 가격은 2026-12-31까지의 소개 가격이며 2027-01-01부터 `$1.50 / $7.50`으로 바뀐다. 출력 요금에는 thinking token이 포함되므로 일반 출력 token과 thinking token을 함께 기록한다. `gemini-3.7-flash`와 `3.6-flash`는 현재 3.8과 가격이 같으면서 이전 세대이고, `gemini-3.5-flash`는 오히려 더 비싸므로 초기 후보에서 제외한다. `gemini-3.1-pro-preview`는 높은 비용과 preview 상태 때문에 본 재현이 끝난 뒤 성능 상한을 소수 case로 확인할 때만 다시 검토한다.

첫 재현에서는 모든 외부 호출을 `gemini-3.8-flash/low` 하나로 통제한다. 동일 task의 성공·호출 수·token·latency·비용을 확인한 뒤에만 `gemini-3.5-flash-lite/minimal`을 추가한다. 처음부터 controller와 actor에 서로 다른 model을 배치하면 코드 재현 실패와 model 능력 차이가 섞이므로 피한다. 현재 기준 model인 `qwen3-next-80b-a3b-instruct`와 Gemini 사이에는 공통 Minecraft 평가 결과가 없으므로, 성능이 동급이라는 주장은 하지 않고 단일 task 및 대표 VillagerBench case에서 검증한다.

### 3. 구현에 필요한 경계 정리

현재 공개 코드의 `GoogleLanguageModel`은 오래된 `google-generativeai`와 `gemini-pro`에 고정돼 있어 최신 Gemini의 직접 대체 경로가 아니다. 후속 구현에서는 `model/openai_models.py`, `env/minecraft_client.py`, `pipeline/retriever.py`, `agent_demo.py`, `auto_gen_gpt_task.py` 등에 남은 중개 endpoint 기본값·예시를 제거하고, 공식 Google SDK 기반의 하나의 Gemini adapter로 Task Manager, Data Manager, Controller와 Base Agent 호출을 연결한다. Model ID와 `thinking_level`은 코드 상수가 아니라 실행 설정으로 분리하고 API key는 추적하지 않는 환경 설정에서 읽는다.

이 변경은 VillagerAgent의 task decomposition, assignment, state management와 action contract를 바꾸기 위한 것이 아니다. 먼저 provider 경로만 교체하고 동일 prompt·응답 parsing·tool contract의 회귀를 확인한다. 공식 API의 Search grounding, File API와 기타 내장 도구는 baseline에서 사용하지 않아 기존 agent가 가진 정보와 행동 범위를 보존한다.

### 4. 로컬 model 대안과 역할

외부 API 통일과 로컬 model 선택은 별도 문제로 관리한다. 로컬 model은 비용 절감용 즉시 대체재로 단정하지 않고, MineSkynet이 비교하려는 연산·메모리 제약이 다른 actor tier를 구성할 후보로 둔다.

| 후보 | 특징 | 잠정 역할 |
| --- | --- | --- |
| Gemma 4 E4B | 공식 추정 load memory가 BF16 17.9GB, SFP8 8.9GB, Q4 약 4.5GB인 경량 model | 강한 자원 제약을 가진 edge actor와 하위 capability tier |
| Gemma 4 12B | 공식 추정 load memory가 BF16 26.7GB, SFP8 13.4GB, Q4 약 6.7GB이며 system role과 function calling 지원 | 3090에서는 FP8·Q4 중심의 중간 local actor 후보 |
| Qwen3.5 9B | 262K native context와 OpenAI-compatible vLLM serving을 지원하고 기존 Qwen 계열 prompt·adapter와 가깝다 | 기존 코드 변경을 줄이는 범용 local actor 후보 |

Gemma의 E4B–12B 조합은 memory·compute tier 차이를 명시적으로 구성하기 쉽고, Qwen3.5 9B는 현재 Qwen 기반 코드와의 호환성이 장점이다. 어느 model을 채택할지는 일반 benchmark 점수만으로 결정하지 않고 동일한 VillagerAgent prompt에서 action format 준수, tool 선택, timeout, VRAM, token throughput과 task completion을 측정한 뒤 판정한다.

### 5. 현재 합의와 남은 검증

현재 합의는 중개 API를 본 실행 경로에서 제거하고, 외부 호출은 유료 Google API로 통일하며, `Gemini 3.8 Flash/low`와 `Gemini 3.5 Flash-Lite/minimal`만 우선 검증하는 것이다. 로컬 후보는 Gemma 4 E4B·12B와 Qwen3.5 9B로 유지한다. 아직 adapter 변경, credential 설정, 외부 호출과 benchmark는 수행하지 않았다.

다음 단계에서는 먼저 공식 Gemini adapter의 단일 요청과 token accounting을 확인하고, 이후 동일 model로 `tiny_start.py`의 한 task를 실행한다. 이 결과가 있어야 외부 model tier와 로컬 actor tier를 섞는 routing 실험으로 확장할 수 있다.

### 6. 공식 근거

- [Gemini API model 목록](https://ai.google.dev/gemini-api/docs/models)
- [Gemini API 가격과 유료 tier의 data-use 조건](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini 3.8 Flash 사양](https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash)
- [Gemini thinking 설정](https://ai.google.dev/gemini-api/docs/thinking)
- [Gemma 4 사양과 추정 memory 요구량](https://ai.google.dev/gemma/docs/core)
- [Qwen3.5 9B 공식 model card](https://huggingface.co/Qwen/Qwen3.5-9B)

---

## 2026-09-23 — VillagerAgent 4단계: 외부 LLM 호출 전 초기화 검사

### 1. 검사 목적과 범위

VillagerAgent의 제어 평면이 외부 추론이나 Minecraft 행동을 시작하기 전에 Python source와 설치 dependency만으로 생성되는지 확인했다. 검사 대상은 실제 `VillagerBench` virtual environment, 단일 `Alice` 등록, 초기 상태의 `DataManager` 반영, `TaskManager`, `GlobalController`와 controller가 생성하는 단일 `BaseAgent`다. Task decomposition을 시작하는 `TaskManager.init_task()`와 agent action, embedding 및 LLM 요청은 이 단계에 포함하지 않았다.

원본 저장소의 log·cache를 삭제하거나 덮어쓰지 않도록 source를 `/tmp/villager-init-smoke.wrPnsm/repo`에 복제하고 `.venv`와 Node dependency는 기존 설치를 읽기 전용 실행 기반으로 사용했다. 복제본에서는 retriever의 import-time credential·중개 endpoint 설정을 제거하고 embedding client를 실제 retrieval 시점까지 만들지 않도록 시험 patch를 적용했다. LLM client에는 호출 권한이 없는 dummy key와 연결 불가능한 `http://127.0.0.1:9/v1`을 주입했으며 Python audit hook으로 모든 `socket.connect`를 실패시키도록 했다. 따라서 초기화가 실수로 외부 호출을 시도하면 검사가 즉시 실패하는 조건이다.

### 2. 초기화 결과

Python 3.10.20 격리환경에서 검사는 exit code 0으로 끝났다. 다음 객체와 역할 연결이 생성됐다.

| 확인 항목 | 결과 |
| --- | --- |
| `VillagerBench` | `_virtual_debug=True`로 생성하고 `Alice` 및 원본 QuickStart의 tool 11개 등록 |
| 초기 상태 반영 | 한 agent의 virtual state를 `DataManager.update_database_init()`에 반영 |
| `TaskManager` | 생성 성공, LLM role `TaskManager` 및 실제 agent tool description 연결 |
| `DataManager` | 생성 성공, LLM role `DataManager` 연결 |
| `GlobalController` | 생성 성공, LLM role `GlobalController` 연결 |
| `BaseAgent` | 실제 `VillagerBench.agent_pool`의 `Alice` 한 명으로 생성 |
| model client | 현재 기준 문자열 `qwen3-next-80b-a3b-instruct`로 client 객체 생성 |
| Retriever client | 생성되지 않음; 실제 retrieval 전까지 lazy 상태 유지 |
| 외부 LLM·embedding·기타 network 요청 | audit 결과 0건 |

이는 **제어 평면 생성자 수준의 import·dependency·객체 연결이 통과했다는 결과**이며, task decomposition, controller assignment, Minecraft action 또는 benchmark 성공을 의미하지 않는다. 향후 Google adapter로 교체한 뒤 동일 검사를 다시 통과해야 provider 변경의 초기화 회귀가 없다고 판단할 수 있다.

### 3. 확인된 숨은 결합과 경고

`TaskManager`가 import하는 `pipeline/retriever.py`는 module import 시점에 저장소 root의 `API_KEY_LIST`를 읽고 `OPENAI_API_BASE`를 `https://api.chatanywhere.tech/v1`로 설정한 뒤 `OpenAIEmbeddings` 객체를 생성한다. 실제 embedding 요청은 발생하지 않지만, 현재 실제 저장소에는 `API_KEY_LIST`가 없으므로 dummy fixture 없이 같은 초기화를 실행하면 외부 호출 전에 파일 오류가 발생한다. 중개 API 제거 작업에서는 이 import-time credential·endpoint 결합을 제거하고, retriever가 실제 사용될 때 공식 provider 설정을 주입받도록 바꿔야 한다.

Clean-copy 검사에서는 외부 API와 무관한 초기화 전제 두 개도 확인했다. 첫째, `VillagerBench.__init__()`은 `.cache/state.json`을 쓰기 전에 `.cache`를 생성하지 않으므로 clean checkout에서는 `FileNotFoundError`가 발생한다. `/tmp` fixture에 runtime 디렉터리를 명시적으로 준비한 뒤 이 단계를 통과했다. 둘째, `VillagerBench.virtual_env()`에는 `inventory`가 없지만 `DataManager._process_agent()`는 이를 필수 key로 읽어 `KeyError`가 발생한다. 시험 복제본의 virtual fixture에 `inventory: []`를 추가한 뒤 실제 초기 상태 반영까지 통과했다. 두 수정은 virtual/offline 초기화 contract만 보완하며 실제 Minecraft server의 상태 schema를 바꾸지 않는다.

Google dependency에서는 Python 3.10 지원이 2026-10-04 이후 새 `google.api_core` release에서 종료될 예정이라는 warning이 발생했다. 현재 초기화를 막지는 않지만 공식 Gemini adapter를 도입할 때 Python 3.11 이상 profile 또는 compatible version pin을 함께 검토한다.

첫 실행에서는 process가 매우 빠르게 끝나면서 Python `javascript` bridge의 daemon `com_io` thread가 종료 중 예외를 출력했다. 두 번째 검사에서 controller executor와 Node bridge process/thread를 명시적으로 종료하자 같은 예외 없이 exit code 0으로 끝났다. 이는 현재 초기화 blocker로 판정하지 않되, 실제 bot lifecycle 검사에서 정상 종료 경로가 bridge까지 정리하는지 다시 확인한다.

### 4. 다음 단계 진입 조건

`/tmp` 격리 복제본에서 import-time provider 결합을 lazy initialization으로 바꾸고 clean-start 전제 두 개를 보완한 조건으로 **4단계의 전체 pre-call 초기화는 통과했다**. 원본 VillagerAgent source에는 시험 patch를 적용하지 않았다. 다음 5단계인 실제 LLM 요청에 들어가기 전에는 검증된 최소 수정 중 `.cache` 생성과 virtual `inventory` schema를 원본에 반영할지 결정하고, 합의한 외부 공급자 정책에 따라 중개 endpoint·import-time credential 결합을 제거한 공식 Gemini adapter의 단일 요청·token accounting을 검증한다. 이 변경에서도 VillagerAgent의 prompt, task decomposition, assignment와 action contract는 유지한다.

---

## 2026-09-30 — 이번 랩미팅 목표: benchmark 검증과 문제 지점 식별

이번 랩미팅까지의 우선순위는 새로운 scheduler나 협업 정책을 바로 구현하는 것이 아니라, **현재 VillagerAgent benchmark가 실제로 실행·측정되는지 끝까지 검증하고 그 결과를 해석할 최소 개념과 문제 후보를 준비하는 것**이다. 이는 MineSkynet의 이기종 과제 할당과 agent 수 증가에 따른 Decomposer–Controller 병목 조사의 공통 선행조건이다.

### 1. VillagerAgent benchmark 실행 검증 완료

이전에 정한 재현 절차의 남은 단계를 이어서 수행한다.

1. `tiny_start.py`의 단일 task가 Task Manager의 분해, Controller의 배정, Base Agent의 실행과 종료까지 도달하는지 확인한다.
2. 실제 LLM 호출 수, prompt·completion·thinking token, latency와 비용 기록이 실행 결과와 함께 남는지 확인한다.
3. farming 또는 construction의 단일 benchmark case를 실행한다.
4. scenario judger가 completion score와 필요한 benchmark metric을 생성하는지 확인한다.
5. construction, farming, room escape 시나리오 모두 검증 완료한다.

첫 완료 기준은 논문의 전체 수치를 재현하는 것이 아니다. **통제된 benchmark case 하나가 시작부터 평가까지 완주하고, 실패하더라도 어느 단계에서 왜 실패했는지 재현 가능한 로그가 남는 것**을 benchmark 검증 완료로 본다. 원본 코드 결함, 환경 호환 patch, model/provider 교체로 생긴 차이는 구분해 기록한다.

최소 보존 근거는 사용 commit과 Python·Node·Minecraft·model 설정, task와 world/seed·agent 수·tool 구성, 생성된 subtask와 dependency, Controller assignment와 validation 결과, actor action·timeout·retry·failure, LLM 호출·token·비용, 최종 judger 출력이다.

### 2. 논문 metric·수식과 OS/network 개념 요약

실행 결과를 해석할 정도의 용어와 수식만 간단히 정리하며 논문 전체 이론을 별도 연구주제로 확장하지 않는다.

#### 2.1 VillagerAgent benchmark와 metric

- VillagerBench의 Construction, Farm-to-Table Cooking, Escape Room이 각각 무엇을 평가하는지 한 문장으로 정리한다.
- Completion Rate `C`, Efficiency `E`, Balanced Agent Utilization `B`, Agent Contribution Rate `ACR`, Visual Hallucination Rate `VHR`, Escape Room Dependency Complexity `D`의 입력과 의미를 논문 수식에 맞춰 요약한다.
- 각 metric이 MineSkynet 질문에 그대로 사용 가능한지 구분한다. 특히 `B`는 이기종 환경에서 고성능 actor에 더 많은 작업을 주는 합리적 할당을 불공정으로 볼 수 있으므로 주 지표로 자동 채택하지 않는다.
- Table 6에서 agent 수에 따라 completion, efficiency와 balance가 어떻게 변하는지 재확인한다.

#### 2.2 OS/network 개념

[`os_network_idea.md`](./os_network_idea.md)를 바탕으로 scheduling의 completion·makespan·throughput·waiting time·utilization, FCFS와 convoy effect, SJF/SRT의 실행시간 예측, ready/running/blocked 상태, 재할당 비용, task DAG의 width와 critical path, queue backlog·service capacity·backpressure, synchronization과 resource competition을 발표용으로 압축한다.

여기서 congestion은 패킷 계층의 TCP 혼잡이 아니라 우선 **작업 생성·도착 속도가 Decomposer, Controller 또는 actor의 처리 능력을 넘어 queue가 누적되는 현상**으로 제한해 사용한다.

### 3. 논문과 실험 결과에서 문제 지점 파악

이번 단계의 목표는 원인을 확정하거나 최적 agent 수를 제안하는 것이 아니다. 논문이 충분히 설명하지 않은 현상과 실제 실행에서 관측되는 문제를 가설 수준으로 분류한다.

| 계층 | 확인할 문제 | 최소 관측 근거 |
| --- | --- | --- |
| Task Decomposer | 병렬 작업을 직렬 DAG로 만들거나 task를 지나치게 크거나 작게 나누는가 | subtask 수, dependency, ready-task 수, graph 재생성 |
| Agent Controller | ready task와 free agent가 있어도 candidate·배정 정책 때문에 유휴가 생기거나 LLM 판단 비용이 커지는가 | assignment, validation 탈락, 배정 대기, Controller token·latency |
| Execution/State | actor들이 공간·자원·API·server를 두고 충돌하거나 오래된 상태로 중복 행동하는가 | timeout, retry, action collision, state update와 실행시간 |

VillagerAgent의 *Agent Collaboration and Performance Dynamics*와 Table 6은 agent 수가 중간 수준까지 성능을 높인 뒤 감소하는 경향을 보여주지만, resource competition과 LLM management complexity를 원인별로 검증하지 않았고 task별 최적 agent 수의 범위도 제시하지 않았다. 따라서 benchmark 로그에서 다음 질문에 답할 단서를 찾는다.

1. agent가 idle일 때 실행 가능한 ready task가 존재했는가?
2. Decomposer가 만든 DAG의 동시 실행 가능 폭이 agent 수보다 작았는가?
3. candidate 제약 또는 Controller 응답·validation 때문에 배정이 지연되었는가?
4. actor 수 증가가 action 충돌, retry, state staleness 또는 LLM/API 대기를 늘렸는가?
5. 성능 저하가 control-plane 정책 문제인지 고정 workload의 정상적인 병렬성 포화인지 구별할 수 있는가?

세부 계측과 원인 분리 실험은 [`agent_efficiency_blueprint.md`](./agent_efficiency_blueprint.md)에 임시 초안으로 유지한다. 이번 랩미팅에서는 benchmark 실행으로 직접 확인된 사실과 아직 추측인 항목을 나누어 보고한다.

### 4. 산출물과 완료 기준

이번 보고는 다음 세 산출물로 제한한다.

1. **Benchmark 검증 기록:** 단일 case의 실행 경로, 설정, 로그, metric 생성 여부와 남은 blocker
2. **한 장 분량의 개념 요약:** VillagerAgent benchmark·metric 수식과 직접 관련된 OS/network 개념
3. **문제 후보 목록:** 논문 결과와 재현 실행에서 확인한 Decomposer, Controller, execution/state 계층의 문제와 증거 수준

Benchmark가 성공하면 생성된 score와 비용을 보고한다. 실패하면 마지막으로 통과한 단계, 재현 명령, 원본 결함과 환경 문제의 구분을 제시한다. 새 정책 구현, 최적 agent 수 탐색과 이기종 scheduler 비교는 이 세 산출물을 확보한 뒤의 다음 단계로 둔다.

---

## 2026-09-30 — Benchmark 검증 1-1: `tiny_start.py` 단일 task 완주

### 1. 검증 목적과 조건

정식 VillagerBench case에 진입하기 전에 단일 task가 Task Manager의 분해, Controller 배정, Base Agent의 Minecraft 행동, self-reflection과 정상 종료까지 이어지는지 확인했다. 실행 대상은 `integration/villager-control-plane` branch의 commit `73b0299`이며, 로컬 Vanilla Minecraft 1.19.2 server와 공식 Gemini API의 `gemini-3.8-flash`, `thinking_level=low`를 사용했다.

`tiny_start.py`의 조건은 Alice 한 명, `Alice talk with yubo` task, 최대 실행시간 5분, 성공 또는 실패 1회 뒤 종료다. credential은 권한 `600`의 `/tmp/mineskynet-gemini.env`에서 주입했고 저장소에는 기록하지 않았다.

### 2. 실행 결과

실행은 약 33초 뒤 exit code 0으로 종료됐다.

1. Alice가 Minecraft server에 접속했다.
2. Task Manager가 `Alice uses chat to talk with yubo`라는 단일 subtask와 milestone을 생성했다.
3. Controller가 해당 task를 Alice에게 배정했다.
4. Base Agent가 `talkTo`와 `waitForFeedback` 두 action을 실행했다.
5. `talkTo`는 server에서 실제 chat message로 확인됐고, 존재하지 않는 yubo에게서 10초 동안 응답이 없었다.
6. self-reflection은 task 요구가 대화 응답 수신이 아니라 메시지 전송이므로 성공으로 판정했다.
7. worker, task execution, task processing thread가 종료되고 Alice가 server에서 연결 해제됐다.

Minecraft server는 실행 후에도 `healthy` 상태를 유지했다. tracked source 변경은 발생하지 않았다. 이 결과로 **단일 task의 분해–배정–행동–반영–종료 제어 흐름은 현재 환경에서 완주 가능함**을 확인했다.

### 3. 범위와 다음 단계

`tiny_start.py`는 scenario judger가 연결된 정식 benchmark가 아니므로 `data/score.json`은 비어 있다. 따라서 이 결과는 benchmark completion metric 생성이나 논문 수치 재현을 의미하지 않는다. 다음 1-2 단계에서 이번 실행의 LLM 호출 수, token, latency와 비용 기록의 일관성을 검증한 뒤 farming 또는 construction의 단일 benchmark case와 scenario judger를 확인한다.

### 4. 낮은 우선순위 관찰사항

Controller가 task 성공을 기록한 직후 Task Manager가 후속 subtask 생성을 한 번 시작했고, 그 응답을 받은 뒤 processing thread가 종료됐다. 종료 신호와 재계획 loop의 순서 때문에 불필요한 LLM 호출이 한 번 발생했을 가능성이 있다. 현재 단일 실행 비용에서 심각한 blocker로 보이지 않고 전체 benchmark 검증보다 우선순위가 낮으므로, 이번 단계에서는 수정하지 않고 향후 control-plane 비용·병목 계측 항목으로만 남긴다.

---

## 2026-09-30 — Benchmark 검증 1-2: LLM 호출·token·비용 기록 확인

### 1. Episode 단위 기록 결과

`tiny_start.py`의 `VillagerBench` 생성 시 `data/tokens.json`과 `data/llm_inference.json`이 초기화되므로, 다음 값은 이전 smoke test를 포함한 누적치가 아니라 1-1 episode의 기록이다.

| 항목 | 기록값 |
| --- | ---: |
| 성공한 LLM request | 8회 |
| prompt token | 12,768 |
| completion token | 807 |
| provider가 반환한 total token | 14,003 |
| thinking token으로 분류된 값 | 0 |
| 추정 비용 | $0.01260225 |
| control-plane inference latency 합계 | 약 9.036초 |

가격 계산은 `gemini-3.8-flash`의 현재 adapter 설정인 입력 `$0.75/1M token`, 출력 `$3.75/1M token`과 일치했다. `data/action_log.json`에는 Alice의 `talkTo`, `waitForFeedback` 두 action이 기록됐고 Task Manager·Data Manager·Global Controller의 prompt와 response도 역할별 UI log에 남았다. 따라서 **episode별 LLM 호출 수, 입력·출력 token, 비용과 action 기록 경로는 작동함**을 확인했다.

### 2. 계측 한계

`tokens_used`는 14,003이지만 prompt와 completion의 합은 13,575로 428 token의 차이가 있다. 현재 adapter는 provider가 total usage에 포함한 이 차이를 cached·reasoning·기타 token 중 무엇인지 분류하지 못하며, thinking token은 0으로 기록했다.

또한 `data/llm_inference.json`의 약 9.036초는 `GoogleLanguageModel.few_shot_generate_thoughts()`를 통과한 control-plane 호출 5회의 latency 합과 정확히 일치한다. actor가 LangChain `ChatOpenAI` 경로에서 수행한 3회 호출은 token·비용 callback에는 포함되지만 이 latency 합계에는 포함되지 않는다. 따라서 현재 기록은 총비용 산정에는 사용할 수 있지만 component별 latency 분석에는 actor 계측 보완이 필요하다.

이 두 항목은 정식 benchmark 실행을 막는 blocker는 아니므로 수정 우선순위를 낮게 두고, 후속 성능·병목 분석 전에 보완할 계측 과제로 남긴다. 다음 1-3 단계에서는 Construction의 단일 benchmark case가 실제 scenario 설정, actor 실행과 judger까지 도달하는지 확인한다.

---

## 2026-09-30 — Benchmark 검증 1-3: Construction Task0 단일 case 완주

### 1. 실행 조건

Table 6의 가장 단순한 Construction `Task0`을 1-agent 조건으로 선택했다. 목표 구조는 `cut_sandstone`, `terracotta`, `torch`를 `[-8,-60,0]`부터 수직으로 배치하는 3-block desert lamp이며, `gemini-3.8-flash/low`와 Alice 한 명을 사용했다. 전체 batch가 아니라 단일 config만 실행했고 결과 경로는 다음과 같다.

```text
MineSkynet-villager-agent/result/
  gemini-3.8-flash_construction_task0_1p_validation_20260930_retry1/
```

Conda 환경은 별도 `/tmp` Python shim 없이 다음 방식으로 실행했다.

```bash
conda run --no-capture-output \
  -p /home/pluto2479/Documents/MineSkynet-villager-agent/.venv \
  python start_with_config.py
```

이 방식은 하위 judger process의 `python`도 같은 Conda 환경에서 찾게 하므로, `.venv/bin/python`만 직접 실행해 하위 `PATH`에서 발생했던 `FileNotFoundError`를 제거했다.

### 2. 환경 초기화 전제와 첫 실패

첫 Construction 시도에서는 `build_judge`가 operator가 아닌 상태로 다수의 world 초기화 명령을 전송해 Minecraft server에서 `Kicked for spamming`으로 퇴장했다. judger process는 연결이 끊어진 뒤에도 `.cache/load_status.cache`를 `loaded`로 기록했기 때문에 Alice는 기존 overworld 위치 `y=73`에 남았고 시험장 teleport와 재료 지급을 받지 못했다. 이 상태에서 actor가 `y=-60`까지 굴착하려는 잘못된 재계획을 반복하기 시작해 비용 증가 전에 실행을 중단했다.

재실행에서는 연구자가 로컬 offline server의 `build_judge`와 Alice에 OP를 부여했다. 이후 judger는 world 정리, 시험장 구성, Alice teleport, 재료 지급과 blueprint 설명 생성을 완료했다. 실행 종료 후 두 계정 모두 `deop`했으며 Minecraft server는 `healthy` 상태를 유지했다.

### 3. 최종 실행 결과

Alice는 시험장 `[-4,-59,1]` 부근에서 시작했고 inventory에 필요한 세 재료를 받았다. Task Manager는 아래 순서로 하나씩 subtask를 생성했다.

1. `cut_sandstone`을 `[-8,-60,0]`에 배치
2. `terracotta`를 `[-8,-59,0]`에 배치
3. `torch`를 `[-8,-58,0]`에 배치

각 단계에서 첫 `placeBlock`이 실패하거나 불명확한 상태를 반환한 뒤 `equipItem` 관측에서 실제 block 배치가 확인되는 동작이 있었지만, server log와 judger는 세 좌표의 변경을 모두 확인했다. 최종 score는 다음과 같다.

| Metric | 결과 |
| --- | ---: |
| `block_hit_rate` | 1.0 |
| `view_hit_rate` | 1.0 |
| `efficiency` | 16.89002316417593 |
| action `use_time` | 18.0초 |
| `complexity` | 2.9066666666666667 |
| 종료 사유 | `complete task` |

Judger의 중간 측정도 `0 → 1/3 → 2/3 → 1` 순서로 상승했다. 따라서 **정식 Construction scenario의 world 초기화, blueprint 전달, Decomposer–Controller–actor 실행과 scenario judger의 completion metric 생성 경로가 한 case에서 완주됨**을 확인했다.

### 4. 호출 비용

해당 성공 episode의 기록은 다음과 같다.

| 항목 | 결과 |
| --- | ---: |
| 성공한 LLM request | 24회 |
| prompt token | 70,911 |
| completion token | 3,263 |
| provider total token | 75,124 |
| thinking token으로 분류된 값 | 0 |
| 추정 비용 | $0.0654195 |

작은 3-block task임에도 반복적인 계획, 상태 요약, reflection과 actor action 생성 때문에 `tiny_start.py`보다 호출량이 크게 늘었다. 이는 이후 component별 호출과 불필요한 재계획을 구분해 볼 근거가 된다.

### 5. 남은 실행기 문제

Judger는 score와 `end` 상태를 정상 생성하고 Alice와 `build_judge` 연결을 종료했지만, `start_with_config.py` parent process는 자동으로 빠져나오지 않았다. 결과 파일이 모두 보존된 것을 확인한 뒤 parent를 수동 중단했다. 이는 benchmark 결과의 성공 여부와 별개로 launcher lifecycle·process cleanup 결함이다.

또한 실패한 첫 시도의 산출물은 기존 결과 디렉터리에 보존했으며 성공 결과로 덮어쓰지 않았다. 다음 단계에서는 생성된 score의 의미와 논문 metric 정의를 대조하고, 필요하면 launcher 종료와 OP 전제를 재현 절차에 명시한다.

---

## 2026-09-30 — Benchmark 검증 1-4: scenario judger metric 생성 경로

### 1. 판정

Construction과 Farming의 단일 case에서 scenario judger가 실행 결과 디렉터리에 `score.json`, `action_log.json`, `tokens.json`을 함께 생성하는 것을 확인했다. 따라서 **행동 로그에서 scenario별 completion과 efficiency를 계산해 episode 산출물로 보존하는 기본 경로는 작동한다.** 다만 세 scenario가 같은 metric schema를 구현하지 않으므로, 현재 출력 전체를 논문 표의 공통 metric으로 바로 간주할 수는 없다.

| Scenario | 실제 생성 metric | 확인 결과 |
| --- | --- | --- |
| Construction Task0 | `block_hit_rate`, `view_hit_rate`, `efficiency`, `use_time`, `complexity` | `1.0`, `1.0`, `16.8900`, `18초`, `2.9067` |
| Farming Task0 | `score`, `cooperation`, `efficiency`, `balance`, `use_time` | `100`, `100`, `13.3333`, `1.0`, `9초` |
| Escape Room | `complete_score`, `complexity_score`, `efficiency`, `balance`, `use_time`을 기록하도록 구현 | world load blocker로 실제 산출 미확인 |

Construction은 block와 facing이 모두 일치할 때 완료되며, Farming은 최종 산출물인 cake checkpoint가 충족되어 `score=100`이 됐다. 두 결과 모두 `end_reason=complete task`를 남겼다.

### 2. metric 해석상 주의점

코드의 `efficiency`는 단순 실행속도나 wall-clock latency가 아니라 scenario별 action-time budget을 실제 `use_time`으로 나눈 값이다. Construction은 `((ln(complexity)+1)×60+180)/18 = 16.8900`, Farming은 `(complexity×40)/9 = 120/9 = 13.3333`으로 저장됐다. 따라서 값이 1보다 클 수 있으며 scenario별 budget 식도 다르다. 논문의 `E`와 대조하기 전에는 두 값을 직접 비교하거나 “16.89배 빠름”으로 해석하지 않는다.

`use_time`도 episode wall time이나 action duration 합이 아니다. 각 action의 초 단위 `start_time`–`end_time` 구간을 합집합으로 병합한 값이어서 1초 미만 action이 0초가 될 수 있다. Farming episode는 실제로 약 1분간 진행됐지만 계산된 action coverage는 9초다. 이 구현 선택은 효율 수치를 크게 만들 수 있으므로 후속 성능 비교 전에 별도 검증이 필요하다.

또한 Construction에는 `calculate_balance()`가 정의돼 있으나 최종 `score.json`에는 balance가 기록되지 않는다. 반대로 Farming의 1-agent `balance=1.0`은 단일 agent에서 자명한 값이라 협업 균형의 증거가 아니다. `cooperation=100` 역시 이번 1-agent 실행에서는 multi-agent cooperation을 입증하지 않는다.

### 3. 자의적 판단

1-4의 완료 기준을 “논문 수치 재현”이 아니라 “judger가 실제 episode의 completion과 보조 metric을 생성하고 원자료와 함께 보존하는가”로 제한했다. 이 기준에서는 Construction과 Farming 경로가 통과했다. 반면 metric 이름과 식의 scenario 간 불일치는 연구 해석 문제로 승격해 숨기지 않고 남겼으며, 공통 metric으로 정규화하는 작업은 수행하지 않았다.

---

## 2026-09-30 — Benchmark 검증 1-5: 세 scenario 최소 case

### 1. 실행 범위와 결과

API 비용과 원인 혼입을 줄이기 위해 각 scenario의 가장 작은 단일 case를 우선 선택했다. 이는 framework의 실행 가능성을 확인하는 smoke validation이며 multi-agent collaboration 성능 재현은 아니다.

| Scenario | 최소 조건 | 결과 | LLM 사용 |
| --- | --- | --- | ---: |
| Construction | Task0, 1 agent, 3-block lamp | 완료 | 24 requests, $0.0654195 |
| Farming | Task0 `cake_0`, 1 agent, 모든 재료가 chest에 존재 | 완료 | 24 requests, $0.0685515 |
| Escape Room | seed 0, 1 room, 1 agent | 검증 완료: `action_time out`과 평가 산출물 생성 | 48 requests, $0.1331415 |

Farming은 Alice가 chest와 crafting table을 찾고, egg·milk bucket·wheat·sugar를 회수해 cake를 제작했다. judger는 `score=100`, `cooperation=100`, `balance=1.0`, `use_time=9초`를 기록했고 launcher도 exit code 0으로 종료됐다.

Escape Room은 두 단계에서 막혔다. 첫 시도는 `minecrafthawkeye`의 CommonJS module 객체를 plugin 함수처럼 전달해 `plugin needs to be a function` 오류로 즉시 종료됐다. 저장소의 `minecraft_server.py`와 동일하게 `require("minecrafthawkeye").default`를 사용하도록 `env/escape_room_judger.py` 한 줄을 호환 수정했다. 이후 judger는 접속을 유지했고 `.cache/task.cache`에 “두 oak pressure plate를 동시에 눌러 iron door를 여는” 유효한 단일 room도 생성했지만, `state_tree.load()` 구간에서 `.cache/load_status.cache`가 160초 동안 `loading`에 머물러 launcher가 `server failed to start`로 종료됐다.

정지 위치를 더 좁히기 위한 process attach는 OS의 `ptrace` 권한에서 거부됐다. 연구자가 지정한 권한 이슈 중단 기준에 따라 추가 권한 요청이나 계측 patch 없이 여기서 중단했다. 임시로 부여한 `escape_judge`와 Alice의 OP는 모두 회수했고 Minecraft server는 `healthy`, 접속자 0명 상태다.

### 2. 관찰된 이슈

1. Farming config가 Construction에서 사용한 `data/map_description.json`을 그대로 가리켜, Task Manager의 `meta-data.recipe`에 이전 3-block blueprint가 섞였다. task description과 Farming judger는 별도 경로를 사용해 cake 제작과 판정은 성공했지만, cross-scenario metadata 오염은 재현성과 decomposition 품질에 영향을 줄 수 있다. Escape 설정에서는 `document_file`을 빈 값으로 바꿨다.
2. Farming의 `withdrawItem(milk_bucket, count=3)`은 action message상 성공했지만 직후 inventory 요약에는 `milk_bucket: 1`로 표시됐다. 실제 craft는 성공해 세 bucket을 소비했으므로 item stack 표현 또는 관측 serialization 문제로 보인다.
3. Construction과 달리 Farming launcher는 judger 종료 신호 뒤 자동 종료됐다. lifecycle 문제는 모든 scenario에 공통으로 재현되지는 않았다.
4. Escape judger의 stderr가 기본 실행에서 `/dev/null`로 버려져 최초 plugin 오류가 단순 `loading` 정지처럼 보였다. 초기화 실패의 원인 보존을 위해 judger stderr capture가 필요하다.

### 3. 자의적 판단과 현재 결론

- Farming은 가장 쉬운 `cake_0`을 선택했다. 재료 획득 난이도를 배제하고 farming world 초기화, chest interaction, crafting, checkpoint scoring 경로만 검증하기 위한 선택이다.
- Escape는 전체 multi-room benchmark 대신 seed 0·1 room·1 agent로 축소했다. 생성된 room의 `min_player=1`을 확인했으므로 agent 수 때문에 불가능한 case를 택한 것은 아니다.
- 사소한 package export 호환성은 저장소 내 이미 작동하는 사용례와 일치시키는 한 줄 수정으로 처리했다. 반면 160초 world-load 정지를 우회하기 위한 timeout 확대나 room loader 변경은 benchmark 조건과 실패 판정을 바꿀 수 있어 자의적으로 적용하지 않았다.

따라서 최초 시도 시점에는 Construction과 Farming 완료, Escape Room 부분 완료로 판정했다. 아래 후속 재검증에서 최종 판정을 갱신한다.

### 4. 임시 권한 허용 후 Escape Room 재검증

연구자가 `kernel.yama.ptrace_scope=0`을 임시 허용한 뒤 동일 설정으로 재실행했다. 이번에는 별도 tracing을 붙이기 전에 world loader가 약 5초 만에 정상 완료되어 이전 160초 정지는 재현되지 않았다. 따라서 이전 현상은 결정적인 상시 blocker가 아니라 비결정적 초기화 정지로 분류한다.

Alice는 room 탐색, 두 pressure plate 발견, 각 plate로의 이동과 iron door 통과를 시도했다. 그러나 task 설명은 두 plate의 동시 활성화를 요구하는데 1-agent가 한 plate에서 다른 plate로 이동하는 방식으로 반복했고, chest로 향하는 경로도 iron door 부근에서 계속 막혔다. 최종 결과는 다음과 같다.

| 항목 | 결과 |
| --- | ---: |
| 종료 사유 | `action_time out` |
| `use_time` | 122초 |
| 기록 action | 22회 (`navigateTo` 12, `scanNearbyEntities` 10) |
| 실패 action | 10회 |
| `efficiency` | 1 |
| `balance` | 1.0 |
| LLM request / 비용 | 48회 / $0.1331415 |

Timeout `score.json`에는 `complete_score`가 빠져 있고 `complexity_score=2.0`만 남았지만, 같은 episode의 `data/score.json`은 실제 room score를 `0`으로 기록한다. 이는 `complexity_score`가 과거의 최대 부분 충족 상태를 유지하거나 timeout 시점의 completion을 명시하지 않는 metric 일관성 문제다. 따라서 `complexity_score=2.0`을 성공으로 해석하지 않고 `end_reason`과 intermediate score를 우선한다.

이 실행으로 Escape Room도 world 생성, Decomposer–Controller–actor 실행, timeout 판정, action·token·score 보존까지 도달했다. 따라서 기존 완료 기준에 따라 **1-5의 세 scenario 실행 경로 검증은 완료**로 갱신한다. 단, task 자체의 성공은 Construction과 Farming 두 case이며 Escape Room case는 실패 종료다.

---

## 2026-09-30 — Decomposer task graph와 Controller 할당 정책 대조

### 1. 논문이 제시한 정책

VillagerAgent의 Task Decomposer는 subtask를 노드로, 선행조건을 directed edge로 표현한 DAG를 생성한다. 선행 노드가 없거나 모든 선행 노드가 성공한 미실행 task가 ready set `N_ready`가 되며, edge가 없는 task들은 병렬 실행할 수 있다. Decomposer는 환경·agent 상태·이전 실행 결과를 보고 매 round 새 subtask를 생성하는 receding-horizon 방식이다. Prompt는 작은 실행 가능 task, agent 수 이하의 subtask, 병렬 실행, `required subtasks`, 관련 문서 경로와 candidate agent를 JSON으로 요구한다.

논문의 Agent Controller는 `AC(E, N_ready, A, S)`로 표현된다. Minecraft 환경, ready task, agent 상태·경험·능력을 LLM에 주고 task–agent 쌍을 JSON으로 생성한다. 제약은 candidate agent만 선택하고, task가 요구한 인원수를 맞추며, 한 agent를 동시에 둘 이상의 task에 배정하지 않는 것이다. 명시적 priority, 예상 실행시간, queue length, hardware·memory 비용 함수는 제시하지 않는다.

### 2. 공개 코드의 실제 생성·ready 정책

`TaskManager`는 LLM 응답의 `description`, `milestones`, `retrieval paths`, `required subtasks`, `assigned agents`를 `Task` 객체로 바꾼다. `required subtasks`의 1-based index가 edge가 되며, predecessor가 생략된 연속 node는 이전 node와 predecessor를 공유해 병렬 sibling으로 취급된다. `Graph.get_open_task_list()`와 Controller의 availability 검사가 `unknown`, predecessor 없음, 필요한 candidate 수만큼 free agent 존재라는 조건으로 ready task를 만든다.

기본 `update` mode에는 논문 설명과 차이가 있다. 현재 graph가 완료될 때마다 성공·실패 trace와 최신 상태를 넣어 LLM을 다시 호출하고, 기존 graph에 `N′`을 합치는 대신 새 graph로 교체한다. 또한 `fill_agents()`가 여러 `assigned agents`를 agent별 동일 task node로 분할하고 각 node의 `candidate_list=[한 명]`, `number=1`로 만든다. 따라서 “어떤 agent가 후보인가”라는 할당 책임의 상당 부분을 Decomposer가 이미 결정한다.

### 3. Controller 구현 두 종류

| 경로 | 실제 정책 |
| --- | --- |
| 논문에 가까운 `pipeline/controller.py` | candidate 수와 요구 인원이 같으면 직접 배정하고, 남은 available task는 환경·경험·상태·free-agent를 넣은 LLM Controller가 선택한다. 반환값은 task 존재, agent 존재, free 상태와 candidate 포함 여부를 검사한다. |
| 이번 benchmark의 `pipeline/controller_tiny.py` | Controller LLM을 호출하지 않는다. ready task의 candidate가 모두 free이면 그 candidate 전원에게 직접 배정한다. |

두 구현 모두 배정된 task를 `task_queue`에 넣고 FIFO로 꺼내 `ThreadPoolExecutor(max_workers=4)`에 제출한다. completion·exception·30분 task timeout을 feedback으로 반영하고 agent를 free 상태로 되돌린다. preemption, work stealing, priority aging, estimated-time scheduling, hardware-aware placement와 backpressure는 없다.

일반 Controller의 validation도 prompt 제약을 완전히 강제하지 않는다. 유효 agent가 한 명이라도 있으면 assignment를 받아들여 `task.number`와 정확히 같은 인원인지 확인하지 않으며, 한 LLM batch 안에서 같은 free agent가 복수 task에 중복 제안된 경우도 validation 단계에서 완전히 차단하지 못할 수 있다. 실패 predecessor는 ready 계산에서 제거될 수 있어 “선행 task 성공 후 실행”이라는 논문 Algorithm 2와 달라질 여지도 있다. 이는 후속 unit test가 필요한 코드 수준 관찰이다.

### 4. 이번 로그에서 확인된 정책

Construction, Farming, Escape의 `TM_history.json`에는 각각 3, 4, 7회의 재분해 round가 남았다. 모든 round는 `required subtasks=[]`, `assigned agents=[Alice]`인 node 하나만 생성했다. Controller log도 각 node를 Alice에게 바로 배정했다. 즉 이번 1-agent 실행은 다음과 같은 순차 feedback loop였다.

```text
상태 관측 → subtask 1개 생성 → Alice에게 직접 배정 → 실행·reflection
          → graph 종료 → 최신 상태로 subtask 1개 재생성
```

따라서 이번 로그는 동적 재계획과 candidate-constrained dispatch가 실제 작동한다는 증거지만, DAG 병렬성, LLM Controller의 agent 선택 품질, ready queue 적체나 최적 agent 수를 검증한 증거는 아니다.

### 5. scheduling·congestion과의 관계 판정

**Scheduling과의 관계는 구조적 유사성이다.** 실제로 precedence-constrained DAG, ready set, eligible-agent 제약, free/busy resource 상태, dispatch queue, 제한된 worker pool, completion·failure feedback이 존재한다. 이는 OS의 ready queue나 DAG scheduling과 동일한 추상화로 계측할 수 있다. 다만 현재 정책은 FCFS·SJF 같은 명시적 수치 algorithm이 아니라 Decomposer의 LLM candidate 지정, 일부 직접 배정, 선택적으로 LLM matching을 결합한 online heuristic이다.

**Congestion과의 관계는 아직 가설 단계다.** `task_queue`와 `result_queue`는 존재하지만 Decomposer가 graph 완료 시에만 agent 수 이하의 node를 생성하므로 지속적인 외부 arrival stream이 아니며, backlog·arrival rate·service rate·queue wait·admission control·backpressure를 측정하거나 제어하지 않는다. 따라서 현재 코드만으로 “congestion control을 한다”고 말할 수 없다. agent 수를 늘린 실험에서 ready task 생성률이 Controller·worker 처리율을 넘고 queue와 대기시간이 누적되는지를 계측해야 구조적 congestion으로 승격할 수 있다.

후속 비교에서는 먼저 `controller_tiny`와 일반 LLM Controller를 구분하고, task별 `created/ready/assigned/start/end`, dependency wait, controller wait, candidate 수, queue 길이와 worker 대기를 기록해야 한다. 그 전에는 이번 1-agent 결과를 scheduling 정책의 성능이나 congestion의 증거로 사용하지 않는다.

---

## 2026-10-06 — 원본 Controller 및 Construction Task6·3인 검증

### 결과와 해석

VillagerAgent 논문의 Controller가 실제로 agent를 선택하는지 확인하기 위해 `controller_tiny.py`가 아닌 원본 `controller.py`로 기존 Task0·1인과 Construction Task6·3인을 실행했다. Task0·1인은 완주했다. Task6·3인은 최초 실행에서 block hit rate 1.0, view hit rate 약 0.867이었으나 시간 초과로 종료됐다. 같은 조건의 수정 전 재실행은 block/view hit rate 모두 1.0으로 완주했다(37 LLM requests, 약 $0.0902). 따라서 첫 시간 초과만으로 Task6의 고정적 실패를 판정할 수 없다.

기본 경로에서는 Decomposer가 각 subtask의 후보를 사실상 한 agent로 고정했고, Controller는 LLM 선택 없이 직접 배정했다. 이는 원본 Controller를 *사용했다*는 사실과 논문의 LLM 기반 *agent 선택을 검증했다*는 주장을 구별해야 함을 보여준다.

이를 검증하려고 동질적 Construction에 한해 선택적 `assignment_policy=controller` 경로를 추가했다. 이 경로는 Decomposer가 agent 중립적인 subtask와 세 agent 후보를 제시하도록 하고, Controller가 free agent와 작업 상태를 입력받아 LLM 배정을 제안·검증하게 한다. 배정 검증에는 후보·가용성·필요 인원수와 동일 batch 내 중복 사용 방지를 반영했다. 실행 중 드러난 DataManager의 미구현 과거 작업 경험 조회는 빈 경험 목록으로 처리했다. 따라서 이번 LLM 배정은 현재 환경·agent 상태에 근거하며, 과거 작업 경험을 활용한 배정 검증은 아니다.

수정 후 Task6·3인 실행에서는 Controller 로그에 LLM의 배정 제안과 수락이 여러 차례 기록됐고, 첫 round에 Alice·Bob·Cindy 각각에게 작업이 배정·실행됐다. 공식 판정은 block/view hit rate 모두 1.0, `end_reason=complete task`, `use_time=15`였다(52 LLM requests, 약 $0.1202). 이 결과는 원본 Controller의 LLM 배정 경로가 실제 실행·완주까지 연결됨을 확인하지만, 수정 전 경로보다 성능이 우수하다는 증거는 아니다. 실행 수가 적고 생성 그래프와 호출 조건도 달라 성능·인과 비교는 보류한다.

관련 코드 변경은 `fda2e2c`에 커밋됐다. 원시 결과는 `result/gemini-3.8-flash_construction_task6_3p_full_controller_20261006_repeat1/` 및 `result/gemini-3.8-flash_construction_task6_3p_controller_llm_20261006_retry1/`에 보존했다. 검증용 Minecraft OP 권한은 회수했고 서버는 종료했다. 10.7 랩미팅 목표의 0) 원본 Controller 검증과 1) 중간 규모 Construction 실행은 완료로 표시한다. 병목·최적 agent 수·이기종 할당 성능 검증은 아직 수행하지 않았다.

---

## 2026-10-06 — Construction Task0–64 구조 비교와 다음 병목 탐색 후보

**연구 목적:** agent 수를 늘렸을 때의 성능 저하를 곧바로 배정 실패로 해석하지 않고, 구조 자체가 제공하는 병렬 작업량과 계획·배정·실행 병목을 분리할 수 있는 다음 과제를 고른다.

`data/building_blue_print.json`의 Task0–64는 하나의 구조를 단계적으로 확대한 것이 아니라, 블록 수가 대체로 증가하도록 배열된 서로 다른 65개 구조물이다. Task0은 3블록·3재료·3층의 수직 램프, 성공한 Task6은 6블록·단일 재료·단층의 수평 구조다. Task20·21은 12블록 단층 도로, Task28·29는 18블록 단층 교차로다. Task64는 48블록·4재료·4층의 우리로 방향 조건도 포함한다. 42블록인 Task57은 14재료·11층인 반면 45블록인 Task60·61은 단일 재료·단층 도로여서, 블록 수만으로 계획 난도나 병렬성을 설명할 수 없다. 범위별 비교표와 후보 순서는 `research/doc/labmeeting_temp.md`의 10.7 랩미팅 항목에 정리했다.

VillagerAgent Table 6에서 Task64의 agent 수별 완료율·효율은 4인까지 상승했다가 8인에서 하락하지만, 이것만으로 Controller 배정 실패나 최적 agent 수의 원인을 식별할 수 없다. MineCollab의 agent 수 증가에 따른 효율 저하 역시 질문·아키텍처·평가 분모가 달라 직접적인 수치 비교 근거가 아니라 탐색 동기다. 고정된 총 작업량을 더 많은 agent로 나누면 1인당 작업량이 줄어드는 것은 자연스러운 현상이다.

**다음 후보:** 기존 Task6을 기준점으로 Task20 또는 21의 단층 도로를 먼저 시도하고, 필요할 때 Task28 또는 29의 교차로로 공간 간섭 가능성을 더한다. Task64는 Table 6과 직접 연결되는 후속 확인 사례로 둔다. 우선 동일 구조·모델·설정에서 2·3인의 생성 그래프, ready 작업 수, 후보 폭, 실제 LLM 배정, 유휴·대기 시간을 확인한 뒤 agent 수를 늘린다. 아직 이 후보들의 병목이나 할당 실패를 실험으로 관찰한 것은 아니다.

---

## 2026-10-06 — Construction Task20 첫 실행: 사건 재구성과 다음 관찰점

**연구상 판정:** Task20·3인 단일 실행에서 Controller LLM은 단층 12블록 도로를 세 줄로 나눈 작업을 Alice·Bob·Cindy에게 중복 없이 배정했다. 관찰된 실패를 현재 단계에서 *할당 정책의 실패*로 분류할 근거는 없다. actor의 조기 종료·부분 완료와 Controller의 실패 누적 종료가 더 직접적인 설명이다. 공식 최종 `score.json` 생성 전 반복 연결 오류를 중단했으므로 마지막 `data/score.json`의 block hit rate `7/12=0.5833`, view hit rate `0.7833`은 **중간값**이다. 중단 시점 기록은 45 LLM requests, 약 $0.1292다.

**실험환경 불일치 조건(사후 확인):** 이 실행은 `server.properties`가 `level-type=minecraft:normal`, `difficulty=easy`, `spawn-monsters=true`인 월드에서 이루어졌다. 반면 저장소 README의 VillagerBench 다중-agent 안내는 `superflat` 지형과 `peaceful` 모드를 요구한다. Construction judger는 지형과 무관하게 시험장 기준 높이를 `y=-60`으로 고정하므로, 현 normal 월드에서는 연구자가 직접 확인한 것처럼 어두운 지하 동굴 안에 유리 케이지가 형성됐다. 따라서 아래 진단은 *이 조건에서의 코드·행동 관찰*이며, 권장 월드 조건에서의 Task20 실패율이나 원 논문 benchmark 재현 결과로 일반화하지 않는다. 지형·밝기·몬스터가 개별 실패를 유발했는지 또한 현재 로그만으로 확정할 수 없다. 기존 Task0·6 결과도 동일 서버 조건의 실행 가능성 검증으로 해석해야 한다.

1. **Alice가 왜 배치 없이 끝났나?** 행동 기록에는 `fetchContainerContents` 두 번뿐이다. 첫 호출은 `item_name`에 재료명을 넣어 인자 오류가 났고, 두 번째는 상자를 열어 재료를 확인했다. 이미 inventory에 smooth sandstone 12개가 있었지만 이동·배치에는 도달하지 않았다. 저장된 `final_answer`는 이동 명령을 작성하다가 문장/JSON이 끝나기 전에 끊긴 듯한 텍스트다. *추정:* 재료 확인과 좌표 해석에 출력 예산을 쓰면서 유효한 다음 tool call을 내지 못했고, agent 실행기가 이를 종료 응답으로 받아들였다. 정확히 모델 출력 길이 제한, 파싱 실패, 혹은 다른 종료 조건 중 무엇이 작동했는지는 현재 파일만으로 확정할 수 없다.
2. **Bob의 마지막 블록은 왜 감지되지 않았나?** 첫 실행의 행동에는 `[-11,-60,0]`, `[-10,-60,0]`, `[-9,-60,0]`에 대한 `placeBlock` 호출은 있으나 마지막 `[-8,-60,0]` 호출이 없다. reflection도 앞의 세 좌표가 관측되고 마지막이 비었다고 판정했다. 따라서 ‘놓았는데 감지 실패’보다 **마지막 배치 시도 전에 첫 actor turn이 끝난 것**이 현재 증거에 맞다. `placeBlock` 메시지의 `can not place`와 `status=true`가 공존하는 이유는 서버가 명령 직후 메시지와 최종 해당 좌표의 블록 존재 여부를 별도로 산출하기 때문이다. 개별 메시지만으로 실패를 판정하지 말고 실제 world state를 확인해야 한다.
3. **Bob은 왜 두 번째에 아무 행동도 안 했나?** Controller는 남은 줄을 Bob에게 재배정했으나 두 번째 `Bob_history.json`의 action list는 0개다. `final_answer`에는 `navigateTo` 호출처럼 보이는 미완성 코드 블록이 남았다. *추정:* 모델이 행동을 의도했지만 실행기가 파싱 가능한 tool call로 처리하지 못해 유효 행동 없이 종료됐다. 이 사건은 실패 3회 한도 도달 **이전**에 기록됐으므로 뒤따른 actor 서비스 종료가 Bob의 0행동을 만든 것은 아니다. 파서의 원시 응답과 종료 사유 계측이 있어야 원인을 확정할 수 있다.
4. **Cindy는 왜 종료 뒤에도 연결을 시도했나?** 첫 줄은 성공 판정됐고 재계획에서 다른 미완료 줄을 맡아 실행 중이었다. Alice·Bob·Bob의 세 하위 작업 실패가 Controller의 전역 `stop_after_fail_times=3`을 소진하자 Controller의 세 관리 스레드가 종료됐고, `env.run()`의 정리가 actor 프로세스들을 종료했다. 그러나 이미 제출한 Cindy의 agent 작업은 완료·취소를 기다리는 처리 없이 남아 `localhost:5002/post_emojimurmur` 등으로 재시도했다. 이 주소는 **외부 LLM API가 아니라 Cindy의 로컬 Minecraft 행동 서비스**다. 다만 agent의 재시도 과정에서 LLM 호출도 추가될 수 있으므로 중단했다. 이는 종료 시 실행 중 작업을 안전하게 취소·수거하지 않는 lifecycle 문제로 보인다.

**다음 실험에서 화면으로 확인할 것:** 연구자가 게임에 접속해 Alice·Bob·Cindy의 위치, 각 좌표의 실제 블록 상태와 배치 시도 시점을 로그 시각과 함께 녹화한다. 특히 Bob의 `[-8,-60,0]`이 실제로 끝까지 비어 있는지, actor가 목표 블록 위에 서거나 서로 이동을 방해하는지 확인한다. 화면만으로 LLM 출력 절단·파싱 종료 원인을 알 수는 없으므로, 병행해 actor turn별 원시 응답, 종료 사유, tool call 수와 Controller의 `active future` 수를 기록해야 한다. 첫 실행 한 번으로 반복성 또는 agent 수 증가의 인과효과는 주장하지 않는다. 원시 근거는 `logs/GlobalController.log`, `logs/TaskManager.log`, `data/action_log.json`, `data/score.json`, `result/gemini-3.8-flash_construction_task20_3p_controller_llm_20261006_trial1/*_history.json` 및 `*_reflect.json`이다.

이 네 가지 현상은 재실행에서 재현되지 않더라도 actor–Controller 종료 경계의 유의미한 진단 단서로 유지한다. 게임 화면은 블록·위치·실제 채팅을, 원시 로그는 LLM 응답·도구 파싱·배정 사유를 각각 검증한다. `img/`의 auto-generation/대화 예시처럼 모든 내부 상태와 사고 과정이 현 Construction 경로에서 게임 채팅에 출력된다고 가정하지 않는다.

---

## 2026-10-06 — VillagerBench 권장 월드 조건으로 서버 재생성

**재현 조건 정정:** 연구자가 직접 접속해 기존 `normal` 월드의 `y=-60` 시험장이 어두운 동굴 안에 있고 몬스터가 나타날 수 있음을 확인했다. 저장소 README는 다중-agent VillagerBench 시험에 `superflat`·`peaceful`을 권장한다. `img/autogen2.png`의 `auto_gen` 상태 채팅, `img/seed.png`·`img/cart.png`의 `meta_judger` 점수, `img/conversition.png`의 Bob→Alice 대화는 평탄한 잔디 지형에서 찍혔지만, 각각 auto/meta/대화 장면이므로 Construction의 채팅 출력을 그대로 증명하지는 않는다. Task20의 앞선 진단에는 위 환경 불일치 조건을 명시했다.

기존 서버를 중지하고 기존 `world` 디렉터리를 `.runtime/minecraft/world-normal-20261006-before-superflat`으로 이동해 삭제 없이 보존했다. 기존 컨테이너도 `villageragent-mc-1.19.2-normal-archive-20261006`으로 이름을 바꿔 보존했다. 같은 로컬 포트 `127.0.0.1:25565`, 같은 `/data` bind mount, Vanilla 1.19.2·2GB 메모리 조건으로 새 `villageragent-mc-1.19.2` 컨테이너를 생성했다. `server.properties`에는 `level-type=minecraft:flat`, `difficulty=peaceful`, `spawn-monsters=false`를 적용하고 새 `world`를 생성했다.

새 서버는 healthy 상태다. 새 `level.dat`에서 `minecraft:flat` 생성기를 확인했고, RCON이 Peaceful 난이도를 보고했으며 `y=-61`의 grass block 조건도 실제 월드에서 통과했다. `ops.json`은 빈 목록이다. 서버·월드 재생성까지만 수행했고 Task20이나 LLM/API 실험은 재실행하지 않았다. 이 시점은 환경 정합성 확인 후 사용자가 중간 커밋을 만들 수 있는 경계다. 이후 실험에서는 이전 `normal/easy` 결과와 새 `flat/peaceful` 결과를 같은 조건의 반복으로 합산하지 않는다.
