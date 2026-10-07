# 랩미팅 대비 임시 문서

## 7.27 랩미팅

> 문서 역할: [`report_log.md`](./report_log.md)에 누적된 작업 보고와 날짜별 논의를 선별·다듬어 교수님께 보고하기 위한 임시 문서다. 현재 목표와 완료 조건은 [`milestone_index.md`](./milestone_goal/milestone_index.md), 연구 원칙은 [`AGENTS.md`](../AGENTS.md)를 따르며, 아래 과거 표현은 당시 맥락 보존을 위해 임의로 고치지 않는다.

- ODYSSEY: Empowering Minecraft Agents with Open-World Skills
  - 문제 의식 : 많은 마크 에이전트 연구들이 테크트리(다이아 얻기 등)을 따르도록 설계됨. 이는 LLM의 능력을 제한함
  - 핵심 구성요소
        1) 40개의 primitive skill, 183개의 compositional skill로 구성된 스킬 라이브러리
            - primitive skill : Mineflayer JavaScript API를 그대로 조작하는 가장 기본적인 스킬들
                - 32개 operational skill : foundational interface with parameterized input (mine(), craft() 등)
                - 8개 spatial skill : 정밀한 포지셔닝, 방향 탐색(orientation) <- 시각 인풋의 부재 때문에 spatial 필수적
            - compositonal skill : 스킬라이브러리 함수들을 재귀적 방식을 통해 구현 -> 복잡한 태스크를 선행조건 함수들을 달성하는 식으로 분해
            - 효율적인 스킬 검색(retrival)을 위해 각 스킬에 대한 설명을 LLM을 통해 텍스트로 생성한 뒤 sentence transformer를 통해 텍스트 정보를 벡터 표현으로 변환.
            - planner-actor-critic 아키텍처 :
                - planner : 포괄적인 계획 생성. 장기 목표 달성을 위해 세부적인 서브 목표들로 분해. 플래너의 인풋 프롬프트는 다음으로 구성
                    1) 궁극적 목표와 행동 제약(<- 태스크는 현 인벤토리에서 가능할 때만 제안하라 등)
                    2) 에이전트 상태 (에이전트와 환경 사이의 상호작용; 배고픔, 체력 등)
                    3) 에이전트의 달성 (현 인벤토리/ 얻은 장비 등)
                - actor : 서브 골을 달성하기 위해 실행 가능한 스킬을 다음과 같이 탐색
                    1) 맥락 쿼리 : 플래너에 의해 생성된 텍스트 기반 서브 골은 sentence transformer에 의해 벡터로 표현
                    2) 유사도 매칭 : 벡터 유사도(내부적으로 코사인/유클리드 등 모름)을 통해 스킬 설명과 서브골 간 유사도 비교
                    3) 스킬 선택 : top-5 유사 스킬중 가장 높은것 택
                - critic : 경험을 문서화 하는 것이 중요. 초기 실행 에러를 일으킬 수 있는 초기 플랜 불일치를 교정하는 피드백-공지 시스템 구축. -> 예상 결과와 실제 결과를 비교 하므로써. 피드백은 세 타입으로 나뉨
                    1) excution feedback : 스킬 실행에 대한 진행 사항을 포착. 성공 여부+ 실패시 가이드라인
                    2) self validation : 인벤토리 변화를 추적해 간단히 성공 여부 추적
                    3) self reflection : 현재 에이전트와 환경에 상태를 평가하여 실패의 원인을 추론
        2) 마크 위키의 QnA로 파인튜닝한 MineMA : LLaMA 3를 마인크래프트 위키에서 추출한 데이터를 통해 도메인 특화 모델로 만듬
            - 데이터셋 생성 : GPT를 통해 마인크래프트 위키에서 크롤링한 데이터를 QnA 쌍으로 가공
            - 모델 파인튜닝 : LoRA를 써 하위랭크 행렬을 학습시킴
            - 모델 평가 : GPT4를 통해 다지선다 질문(multiple choice question)을 통해 마크에 대한 도메인 특화 모델이 되었는지 평가
        3) 모델 잠재력 벤치마크
            - long term planning task : 여러개의 전투 시나리오; 무기와 장비를 만들고 전투. 싱글타입과 멀티타입 몬스터로 나뉨. -> 기준은 남은 체력과 시간으로 측정. 각 전투후 반복적으로 에이전트 최적화
            - Dynamic-immediate planning task : 즉각적으로 환경 피드백이 있는 경우 동적으로 생성하고 계획을 싱행하는걸 평가. -> 여러 파밍 시나리오; 실시간 환경에서의 평가
            - autonomous exploration task : 다음 목표와 적절한 스킬을 고르는 능력 평가. 자원을 찾고, 활용하고, 예상치 못한 상황에 적응하는 능력.
  - ablation study : 플래너와 스킬 라이브러리가 각각 필수적 요소. 하나라도 빠지면 심각한 성능저하.
  - 한계 : 오픈소스 LLM은 할루시네이션이 쉽다. 이를 방지하기 위해 RAG 도입을 고려중. 현재 텍스트 기반 LLM에 초점을 맞춰, 시각적 요소는 거의 배제되었다.

## 7.30 랩미팅

1) 프레임워크 계획 요약
    - 핵심 연구 질문 : 통합 cloud-tier orchestrator가 연산 성능과 local LLM 능력이 서로 다른 Minecraft bot drone들에게 subtask를 적절히 배정하는 구조는 cloud-only, local-only 또는 고정 역할 방식보다 낮은 비용으로 유사하거나 더 높은 협력 task 성공률을 달성할 수 있는가?
        - 핵심 가설
            1. 복잡한 계획만 cloud-tier mothership에 맡기고 실행은 edge drone가 담당하면 cloud-only 방식보다 API 비용을 줄일 수 있다.
            2. agent별 수행 능력을 고려한 task allocation은 agent 차이를 무시한 균등·무작위 배정보다 성공률과 완료 시간을 개선한다.
            3. 병렬화 가능한 subtask를 여러 drone에 배정하면 강한 단일 agent보다 전체 task 완료 시간이 감소한다.
            4. planning, communication, state synchronization 비용을 모두 포함한 뒤에도 일정 조건에서는 edge-cloud 협력의 이득이 남는다.
    - 보유 자원/장비 및 역할
        - (빌리저 에이전트 논문 설명)
        - (오케스트레이터-엣지 프레임워크 구조도)
            - Raspberry Pi: raspberry pi 4b (4gb ram)
            - GTX 1050 Ti 컴퓨터: vram 4gb; cpu/ram 차후 확인
            - RTX 3090 컴퓨터: VRAM 24GB, 현재 주 개발 장비
            - 외부 cloud LLM API: 고난도 계획과 재계획에 제한적으로 사용 (3090에 통합 고려중; vram, ram 용량 넉넉)
    - drone(기존 오딧세이 actor) 대안 LLM모델
        - 기존 llama 3 8b를 기반으로 파인튜닝한 MineMA는 저사양 노드에 올릴 수 없으므로 gemma 3 1B 모델을 기반으로 LoRA를 통해 파인튜닝한다 (훈련 데이터셋은 허깅페이스에 공유됨)
        - 극한으로 양자화 걸면 양자화 수준 INT4, 컨텍스트 윈도우 8k 기준 vram 1.84gb. (axpml 사진)
    - 네트워킹 방법
        - tailscale을 통해 번거로운 포트포워딩/공인IP 또는 같은 공유기 내 연결 강제 문제 우회
        - 일종의 VPN. 설치후 작동시 타 라우터/공유기 환경 내에서도 잘 동작
        - 당연히 진지한 기여로 포장X.
2) 현재 진행상황 요약
    1) 자바 버전 이슈와 nvm 이슈 해결
    2) mineflyer을 통해 cli 환경으로 나무 1개 채굴 테스트 성공
    3) 오딧세이 actor 재현을 위해 MineMA 다운로드 진행중
3) 추후 계획
    - mineMA까지 포함된 온전한 상태에서 나무 채굴 테스트, 작업대 제작 테스트 확인
    - drone 모델로 llama3/mineMA가 아닌 gemma 3 1b로 교체 가능한지 여부; 교체후 똑같이 나무-작업대 테스트

## 8.6 랩미팅

1) 현재 진행상황

- 프로젝트에서 의존성 이슈가 너무 많아 보수 코드를 계속 짜는 것 보다 차라리 의존성 최신화 -> 이후 최신화된 버전 기준으로 보수 코드 패치 방향으로 결정
  - 단, 조금 진행하다가 LoRA를 먼저 해보고 싶다는 생각에 연구 순서상으론 약간 다음인 파인튜닝 먼저 진행
- 허깅페이스에서 데이터셋과 gemma 3 1b 다운로드
- json 포맷에서 NaN은 읽히지 않아 전처리 필요. 또한 중복 데이터들이 있어 preprocessing.ipynb 생성
- 전처리용 가상환경/커널 세팅; 학습 전용 콘다환경 세팅
- train_row를 달리하며 128, 128 과적합(train_row=128,eval_row=128), 1k, 10k로 달리하며 파인튜닝 수행
  - '제작대에 필요한 나무 판자 수는?' (정답 4개)에 대해 과적합, 1k는 통과; 나머지 128과 10k는 실패함
  - 단일 질문 테스트이므로 확정할 순 없지만, 학습 규모에 따라 일관되게 성능향상은 가지지 않는 것으로 보임
  - 다만 오딧세이의 mineMA 활용이 실제로 작업을 수행하는 actor 뿐만이 아닌, planner, reflector 등 여러 부분에서 쓰인다는 점. 그리고 현재 프로젝트 구상안은 actor 노드에겐 고도의 추론과 계획보단 매우 파편화된 subgoal에 대해 적절한 skill 선택을 주력으로 한다는 점에서 아쉬운 추론성능이 발목을 잡을지는 미지수.
    - 따라서 도메인 특화 모델을 actor용 1b 기반, 도메인 지식/추론용으론 더 크고 똑똑한 모델 이런식으로 병행하는게 필요해보임
    - 오딧세이의 in-context적 요소 또한 actor에게 기대하기보단 planner의 task allocation의 품질을 적응 시키는 방식으로 기대중
{
  "run_profile": "memorize_128",
  "prompt": "In Minecraft, how many wooden planks are required to craft a crafting table?",
  "expected_factual_answer": "4 wooden planks",
  "base_answer": "You need **6** wooden planks to craft a crafting table in Minecraft. \n\n(1 wood plank x 6 = 6 planks)",
  "adapter_answer": "The crafting table requires 4 wooden planks to craft it in Minecraft.",
  "reload_inference_peak_vram_gib": 1.976
}

{
  "run_profile": "pilot_1k",
  "prompt": "In Minecraft, how many wooden planks are required to craft a crafting table?",
  "expected_factual_answer": "4 wooden planks",
  "base_answer": "You need **6** wooden planks to craft a crafting table in Minecraft. \n\n(1 wood plank x 6 = 6 planks)",
  "adapter_answer": "To craft a crafting table in Minecraft, you need 4 wooden planks.",
  "reload_inference_peak_vram_gib": 2.028
}
2) 다음 계획
    - INT4로 배포 후 BF16과의 출력정확도, 지연, peak vram을 비교
    - 오딧세이 actor adapter의 엔드포인트 설정
    - 현 작업 완료시 다시 의존성 현대화 작업 진행
3) 피드백

## 8.20 랩미팅

1) 환경 재현 관련 이슈들
    - 추가적인 실험이나 구현 전에 일단 환경 세팅부터 최우선적으로 하는 방식을 선택. 좀 게으른 방식이긴 하지만 추론수준을 최고로 당기고 프로젝트를 탐색시킨 다음 보고서를 작성 -> 작성된 보고서에서 의존성들을 세가지 클래스로 나눔. 나누는 기준은 오딧세이 실험 재현에 필요한 최소기능인가? 따라서 브랜치 상으로 다음으로 관리
        1) odyssey-modernization : 의존성 이슈가 많은 구형 오딧세이에 대해 의존성이 취약한 부분은 대체/삭제/업데이트/보강. 목표는 구형 코드의 기능 재현하면서 의존성 이슈로부터 튼튼하게
        2) mineskynet-core : 1) 이 완료된 후 이 위에 추가적인 제안을 더 붙일것 (다중에이전트 등)
        3) odyssey-legacy : 구형 오딧세이. 브랜치상 master에서 관리
    - 챗봇이 목표를 과도해석하거나 프로젝트 본질에 맞지 않는 경우를 제한하기 위해 일종의 하네스? 구조 도입. 도입 계기는 오딧세이 현대화중, 현대화 작업 자체가 너무 과도하게 분석의 대상이 되고, 세부 목표가 과도하게 세분화되며 늘어지는 경향을 포착. 또한 챗봇과 작성한 문서에 대한 소비자를 다음과 같이 나눴을 때 (1) 1차 연구자 (저, 연구를 수행하는 당사자). (2) 2차 연구자 (교수님/동료 학연생 같이 피드백/코워커) (3) 프로젝트를 모르는 제 3자 로 나눴을 때 (2),(3)은 고사하고 (1)도 챗봇의 분석이나 문서를 따라가지 못한다고 파악. PROMPT.md에 반영
        - 경험적으로는 해당 하네스 도입 이후 논문-구현 간 일대일 대응이 훨씬 명료하고 챗봇도 실제 구현이나 너무 기술적으로 빠져들지 않고 논문에서의 언어를 사용하여 정보를 받는 입장에서 훨씬 간결하다고 느낌.
2) 실제 완료 항목

   ### 논문–코드–dependency 대응 `[~]`

    논문이 설명한 각 기능이 현재 어느 코드와 model에 의해 수행되는지 연결해, dependency를 바꿔도 연구 기능을 잃지 않게 한다.

    - [x] 논문의 각 기능을 source file, dependency, model과 input/output에 연결
    - [~] task, prompt, primitive 40 manifest, 183 skill corpus와 checkpoint 출처·hash 고정
    - [x] dependency를 core, executor, retrieval, model, combat, training으로 1차 분류
    - [ ] 각 profile의 지원 버전, lockfile과 clean-install 절차 작성
    - [~] license, 보안 경고, deprecated API와 유지보수 상태 기록
    - [x] branch 역할과 범위 기반 tag 정책 확정

    세부 근거와 미해결 조건은 [`paper_code_dependency_map.md`](../paper_code_dependency_map.md)에 기록했다. primitive 40개의 논문–source working manifest와 compositional code·description 183쌍의 checksum을 고정했다. Voyager 상속 primitive 18개의 runtime interface fixture, source상 contract 위험의 수정·검증, encoder revision·전처리, retrieval 결과와 clean-install lock은 후속 검증으로 남았다.

   ### Minecraft 실행 계층 `[x]`

    actor가 선택한 JavaScript skill이 실제 Minecraft 상태를 바꾸고, 오류가 나도 다음 실행을 계속할 수 있는지 확인한다.

    - [x] Mineflayer bridge health/version과 request-local bot lifecycle
    - [x] finite position guard와 failure 뒤 bridge 생존
    - [x] `/pause` 없이 mod-free server에서 나무와 작업대 각각 10/10
    - [x] inventory delta, latency, dependency와 Minecraft log 자동 저장
    - [x] bridge·pause bundle·bot lifecycle의 결합 문제와 변경 이유 문서화
    - [x] `a157205`를 `odyssey-modernized-executor-1.19.4` annotated tag로 로컬·원격에 고정

    원본 bridge의 재실행이나 legacy 대비 latency 표는 요구하지 않는다. 현재 실행 계층이 clean install, 정상 행동과 대표 failure recovery를 반복 통과한 것으로 이 범위를 완료한다.
3) 다음 목표 (modernization_milestone.md에 세부사항)
    - 논문–코드–dependency 대응, Skill library와 semantic retrieval 작업 완료
    - 나머지 취약한/불안정한 과제들을 순차적으로 개선.
    - 피드백
        - 기능 전부 재현 & 현대화는 아닐수도 있다 → 일부 까다로운게 있을 수 잇다.
            - 스킬은 많음 → 마크에서 캐고 조합; 작동이 되면 다 되지 않나?
            - 일부가 안될수도 있다.
            - 너무 다양한 태스크 → 판이 너무 커진다. 적당한 태스크 잡는걸 목표 (예를들어 다이아 얻기 까지)
            - 목표를 줬을 때 스킬이 다 있고 적절한 스킬을 조합해서 해결할 수 있나? → 난이도가 (농장만들기나 집만들기처럼 적절한 중간목표)
            - 가벼운 모델은 실패/무거운 모델은 성공할만한
            - 오뎃세이에서 할만한거 전부 최신화하려면 시간이 걸릴수밖에
        - 챗봇 : 챗봇이랑 같이 작업할때 챗봇의 방향이 옳은 방향으로 복잡해지는가? 필수적인가? 내가 컨트롤 가능한 수준인가?
            - 스코프를 적절하게 만들고 계속 쪼지 않는이상 필요이상으로 복잡; 뭘 남기고 뭘 버리는지의 판단도 항상 인간이랑 일치하지 않을수도
            - 선별/축약/요약/판단의 영역이 더 중요해진다
        - 연구주제 : 방향이 헷갈리면 상위 주제가 무엇인지 상기해라; (적절하게 더 작은 목표로 작게 쳐 내거나)
            - 기준 : 남들하던거/권위에 기대긴 함 → 단, 희소하거나 하는게 더 컨트리뷰션 있을수도 (따라하는게 나쁘진 않지만 훌륭한 연구자 → 독창적)

## 8.27 랩미팅

1) 이번주 목표
    - Skill library를 정적으로 정리한 상태에서 실제 재현 가능한 retrieval 입력 계층으로 올리는 것

    1. Primitive runtime 결함 정리
        - `goto`, `getAnimal`의 명백한 구현 오류 수정
        - `feedAnimals`, `cookFood`, `killMonsters`의 contract 위험 확인
        - primitive를 조회·장착·이동·상호작용 등으로 나눠 대표 fixture(고정본) 작성
        - 서버가 필요한 fixture는 실행 명령과 성공 조건을 준비한 뒤 직접 실행

    2. Semantic encoder 조건 고정
        - 공개 코드의 `paraphrase-multilingual-MiniLM-L12-v2` 정확한 revision/checksum 기록
        - max length, pooling, normalization 설정 기록
        - 같은 corpus(말뭉치)를 다시 embedding할 수 있는 manifest(확정본) 작성
            - 같은 입력을 다시 만들 수 있는가?
        - Chroma·LangChain deprecated API 경고 정리
        - retrieval profile의 dependency version/lock 작성

    3. Retrieval fixture 완성
        - top-5를 기본 profile로 구현(의도는 저사양 노드에서 불필요한 연산을 줄이고 추가적인 계산이 유의미하진 않다고 판단)
            - top-10을 별도 profile로 분리
        - 대표 자연어 subgoal 몇 개에 대한 후보와 score 저장
        - index 재생성·재로드 후 후보 순서가 유지되는지 확인
            - 구형/원본 인덱스 사용시 잠재적 문제가 있고 어차피 인코더로서 재현 가능하기 때문에 구형 index 제거
        - 조건과 결과를 고정해 이후 actor 실험의 입력을 통제
        - 빈 환경에서 install → index 생성 → reload → 검색 smoke test
            - 2. 에서 통과하긴 했지만 설치->임베딩->검색 까지 파이프라인 통과

    4. +@
        - 작업을 하면서도 지속적으로 목표를 상기중. 현재 코드 자체의 디버깅/트러블슈팅 뿐만이 아니라 semantic transfomer의 조건 확정이나 clean install 또한 주관적인 입장이지만 파이프라인을 명시적이고 깔끔하게 한다는 측면에서 개인적으로는 타당하다고 생각
        - 추가로 의미상/기능상으로 세부 목표를 묶어 한 보고 단위를 정하고 report_log.md 로 체계화
        - 현대화 마일스톤 문서상으로도

2) 다음 목표
    - 논문–코드–dependency 대응 `[~]` : 미완료된 나머지 항목들 보수
    - Actor와 model service `[ ]`
    - Planner–actor–critic end-to-end `[ ]`
    - 능동 skill lifecycle 보존 profile `[ ]`
        - 대략 2-3주, 보수적으론 3-4주면 완전한 현대화 가능.
    - in context RL이 전통적인 뉴럴넷/딥러닝에서의 온라인학습이나 보조 수단(RAG등) 외에도 실시간으로, 혹은 한 세션의 lifecycle 내에서 적응 가능한 시스템으로서 방법론이 가능한가? (넓게보면 보이저-오딧세이-마인스카이넷도 이 질문의 연장선이라고 넓은 관점에서 해석 가능할지도)
        - 구체적으로는 챗봇등에서 과거 대화 내역 -> 감성분석 및 스코어링 -> 적응이 기존 트랜스포머 only보다 더 효율적으로 가능한가?
            - 막연히 드는 생각이지만 어차피 트랜스포머 구조상 모든 입력을 읽고 다음 토큰을 예측하는 것 이기 때문에 의도적이진 않아도 사용자의 의도에 적응한다고는 생각
        - RLHF등과는 별개로 구분
        - 아직 구체화되고 엄밀한 질문은 아니고 추상적으로 러프하게 던지는 질문

## 9.09 랩미팅

### 1. 이번 주 목표

MineSkynet이 기존 방법보다 무엇을 개선하는지 검증할 수 있도록, **Minecraft 다중 agent 연구에서 재사용할 benchmark를 선정하고 최소 실험 방향을 정한다.** 새로운 benchmark를 먼저 만들기보다 기존 과제와 평가 방식을 우선 활용하며, 기존 평가로 연구 질문을 확인할 수 없을 때만 필요한 조건을 추가한다.

### 2. 관련연구와 benchmark 방향

- **VillagerAgent / VillagerBench**를 기본 benchmark와 현재 상태 기반 작업 할당의 비교 기준으로 유지한다.
  - **CausalMACE**는 VillagerBench를 계승해 dependency와 부하분산을 개선한 연구; 문제 설정과 해결이 매력적이나, 본 연구엔 맞지 않음 (멀티 에이전트엔 빌리저 에이전트 우세 & 공개코드 부재) 따라서 Discussion 후보로 두되, 독립 benchmark로 보지 않는다.
- **MineCollab / MINDCraft**에서는 agent마다 자원·recipe·skill이 나뉘어 협업이 반드시 필요한 조건을 검토한다.
- **TickingCollabBench**에서는 서로 다른 capability와 실제 시간 제약이 작업 할당에 미치는 영향을 검토한다.
- TeamCraft와 Gated Coordination은 각각 멀티모달 일반화와 통신 escalation이 중심이므로 현재 주 후보에서 제외한다.

세 benchmark를 통째로 합치지 않는다. VillagerBench의 과제와 판정 방식을 출발점으로 삼고, MineCollab의 필수 협업과 TickingCollabBench의 이질적·실시간 조건 중 MineSkynet의 연구 질문에 필요한 부분만 선별한다.

### 3. 실험설계에서 정할 내용

Planner와 실행 node의 물리적 분리는 유지한 채, 작업 할당과 누적 경험 활용 방식의 차이를 비교한다. 이를 위해 다음을 이번 주 조사 결과와 연결해 초안으로 정한다.

- 어떤 조건에서 어떤 기존 방법보다 무엇이 개선되는지 나타내는 최소 가설
- prerequisite와 병렬 작업을 함께 포함하면서 구현 범위가 과도하지 않은 대표 과제
- 고정·무작위 또는 현재 상태 기반 할당과 MineSkynet 할당의 비교 방식
- 완료율·완료시간 등 주 지표와 중복 작업·재할당·추론 및 자원 비용 등 필요한 보조 지표
- 선택한 과제를 실행하기 위해 먼저 확인해야 할 최소 skill과 관측 기능

게임 안의 도구·자원 차이와 실제 물리 actor의 model 성능·지연·memory·energy 차이는 구분한다. 후자는 MineSkynet이 측정된 capability와 실행 이력을 작업 배정에 활용할 수 있는지 확인하기 위한 고유 조건이다.

### 4. 이번 주 산출물

다음 랩미팅에서는 **기존 연구는 어떤 조건에서 개선을 입증했고, MineSkynet은 그 평가를 어떻게 재사용해 무엇을 추가로 확인할 것인지**를 설명한다. 이를 위해 benchmark 후보 비교와 최소 실험설계 초안을 준비한다. 과제, 가설, baseline과 지표의 최종 확정은 조사 결과와 피드백 이후에 진행한다.

## 9.16 랩미팅

### 문제상황

1) 실험설계 과정

- VillagerAgent 논문의 VillagerBench 채택 : '이기종 라우팅 환경에서 상이한 에이전트간 연산능력/메모리/vram을 고려한 복합 과제 할당' 이라는 연구 질문에 대해 가장 기준으로 삼기에 적합한 논문이라고 판단. 따라서 villagerBench의 벤치마크를 채택하고 이기종간의 차이를 고려하는 메트릭/추가 측정요소를 설계하거나 도입하는게 적절하다 판단
  - 후술할 논문의 세부 내용 처럼 완수율(C)/효율성(E)/밸런스(B) 세 메트릭을 기준으로 세가지 과업 측정
    - 하지만 밸런스 부분은 '에이전트에게 공평하게 작업 배분이 되는가?' 메트릭이므로 이기종 환경에선 고성능 액터가 더 많은 작업을 받는게 타당할수도
    1) construction cooperation task : 지시 해석 및 할당 능력
    2) farm-to-table cooking task : 환경적 다양성 및 전략적 유연성
    3) escape room challenge task : 동기화 및 순차적 처리

- Collaborating Action by Action 논문의 MineCollab 참고 : 필수적인 협업 조건을 만드는 법에 집중. '동일 능력을 가진 에이전트에서, 어떻게 서로다른 정보/자원/도구들을 가진 에이전트들이 협력해야만 과제를 풀 수 있도록 설계할 것인가?'
  - 에이전트간 자연어 통신을 전제로 하고 상이한 조건/환경/정보 하에 효율적인 협동을 질문하므로 현 연구의 궁극적인 질문인 '서로 다른 기종간 능력차이를 고려해 복합적인 작업 할당을 고려할 수 있나? 그리고 그게 복수의 동일 능력 에이전트와 차이점은?' 이라는 주제에 대해선 모든 요소를 가져오는건 기각.
  - 특히 이 논문에서 다루는 에이전트간 효율적인 자연어 통신 실패 부분은 villagerAgnet 에서는 task decomposer의 테스크 할당 실패, agent controller의 작업 분배 실패로 측정할 동기가 있으나 연구 질문 자체가 비대해질 가능성.
  - 대신 experiments 부분에서 '에이전트 수 증가에 따른 협업 효율 저하' 부분은 mineSkynet에서도 추가로 측정할만한 동기가 있음. villagerAgnet 에선 다루지 않는 문제
    - 즉, 노드간 연산능력을 적절하게 고려한다면 작업 난이도를 고려해 어느 에이전트는 유휴상태로 대기시키고, 어느 에이전트는 일하게 시킬수 있다 라는 가설로 확장 가능성?

- 'Multi-agent Framework for Time-Sensitive Complementary Collaboration in Minecraft' 의 TickingCollabBench 참고 : 수행 계층 actor마다 능력이 상이, 환경 변화, 실제 시간 제약. 어떤 엑터에게 무엇을 언제 배정해야하나?
  - 연구의 질문은 위의 mineCollab처럼 '동일한 에이전트; 하지만 서로 다른 마크 조건. 어떻게 작업을 할당할 것인가?' 인데, 능력/환경 뿐만이 아닌 실시간 시간 제약 또한 다루고 있음
  - 질문할 것은 '서로 다른 연산능력 -> 적절한 과제 배분?' 이므로 이 연구의 접근 방식과는 반대방향으로 '조건들을 동일하게 통제해놓고 에이전트의 지능수준/컨텍스트 윈도우 길이를 달리하여 실험' 이 적절해보임
    - 실제로 물리적으로 서로 다른 노드들을 고집할게 아니라 3090 하에서 다른 수준을 가진 에이전트들을 물리는 것도 고려.
      - 단, 이 방식으로 갈 경우 엄밀하게 '하드웨어 제약 상 적절한 작업 배분' 질문은 희석됨. 그러나 인과적으로 하드웨어상의 제약이 실질적으로 llm 추론능력/기억을 제한하기 때문에 대리변수 느낌으로 표현.
    - 수식 부문을 참고하여 '마크상에서의 상이한 조건 -> 에이전트간 상이한 연산/메모리 조건'으로 변화하여 metric 정의 가능한가?

1) 기존 프로젝트를 엎어야하는 가능성과 깃/로컬 폴더 관리

- 소개한대로 villagerAgnet가 벤치마크 뿐만이 아닌 아키텍처 또한 현 연구질문에 더 근본적으로 적합하다고 생각.
  - 어떤 질문을 구체적으로 던지고 싶은지, 최종목표로부터 방향을 역추적해 현재 단기 목표를 결정할지 가 매우 중요한 부분이었는데 막연하게 오딧세이를 바텀업 방식으로 따라가다가 현 질문과는 맞지 않는다는걸 파악
  - 따라서 구상안은 오딧세이 현대화를 중단하고, 오딧세이에서 살릴 수 있는 부분 (life-long in-context; 지속적인 재계획 및 코드 수정)을 최대한 모듈화 하는 방식 (현 연구목적에 부합한다면)
  - 의존성 문제를 최대한 피하기 위해 JS/파이썬 관련 의존들만 최소한으로 남기고 중요도가 떨어짐에도 강한 의존성 이슈를 불러오는 부분은 가능하면 네이티브/바닐라 코드로 대체
    - 크로마DB, sentence transfomers, gymnasium, 랭체인, 파이썬 자바스크립트 라이브러리, JS babel 등
    - ex) 벡터들을 탐색해야하는 경우, 크로마DB 대신 sqlite+외부 바닐라코드 코사인 유사도 계산
- 그러나 깃 브랜치/워크트리 관리를 어디서부터 손대야할지, 로컬 폴더는 어떻게 손대야할지 감이 안잡히는 상태
  - 로컬은 현재 일단 /Documents 아래에 연구용-오딧세이용-빌리저에이전트용 으로 분할

## 9.23 랩미팅

1) 진행상황
    - [O] 1. Python 3.10 격리환경에서 requirements의 설치 가능 여부와 import를 확인한다.
        - 저장소 내부 `.venv`에 Python 3.10.20 Conda 환경을 생성하고 원본 `requirements.txt`를 그대로 설치했다. LangChain, scikit-learn, Python `javascript`, FlagEmbedding, OpenAI client, Flask, Gymnasium, DashScope, Torch와 Transformers를 포함한 주요 import가 통과했다.
        - 원본 requirements가 `torch`, `transformers`, `optimum`, `auto-gptq` 등의 상한과 runtime profile을 고정하지 않아 2026-09-23 설치에서는 Torch 2.14.0+cu130과 CUDA 13 관련 package가 선택됐고 `.venv` 크기는 약 6.5GB가 됐다. 이는 최소 VillagerAgent 실행 요구가 확인된 결과가 아니라 원본 dependency 선언이 허용한 설치 결과다. LangChain이 요구한 `packaging==23.2`와 Conda 기본 `wheel==0.47.0`의 build-tool 충돌은 runtime package를 변경하지 않고 `wheel==0.45.1`로 맞췄으며, 이후 `pip check`는 `No broken requirements found`를 반환했다.
    - [O] 2. Node dependency를 lock 상태와 함께 설치하고 `js_setup.py`가 모든 module을 load하는지 확인한다.
        - 원본 저장소에는 lockfile이 없으므로 새 lockfile을 생성하지 않는 `npm install --no-package-lock`로 package를 설치했다. 247개 package가 설치됐고 `npm ls --depth=0` 및 `js_setup.py`의 Mineflayer 관련 module load가 통과했다.
        - 다만 caret 범위 때문에 `mineflayer@^4.23.0`은 현재 `4.39.0`으로, `minecraft-data@^3.80.0`은 `3.117.0`으로 해석됐다. Mineflayer 4.39.0과 전이 dependency인 minecraft-protocol 1.68.0은 Node 22 이상을 요구하지만 현재 Node는 20.13.1이어서 engine warning이 발생했다. npm audit은 moderate 12건과 high 1건을 보고했다. `npm audit fix`나 임의 upgrade는 적용하지 않았다. 다음 bot 단계 전에는 원 논문 시기의 버전을 고정할지 Node 22에서 현재 해석 결과를 검증할지 결정해야 한다.
    - [O] 3. Minecraft 1.19.2 server를 준비하고 단일 Mineflayer bot의 접속·종료를 확인한다.
        - `itzg/minecraft-server:java17` image로 Vanilla 1.19.2 server를 `villageragent-mc-1.19.2` container에 실행했다. World와 server data는 Git에서 제외한 `MineSkynet-villager-agent/.runtime/minecraft`에 저장한다.
        -
        container: villageragent-mc-1.19.2
        image: itzg/minecraft-server:java17
        Minecraft: Vanilla 1.19.2
        memory: 2G
        published port: 127.0.0.1:25565 -> 25565/tcp
        online-mode: false
        health: healthy
        - Server log의 `Done (15.378s)`와 `Starting minecraft server version 1.19.2`를 확인했고, host에서 `127.0.0.1:25565` TCP 연결도 통과했다. RCON은 container 내부에서 시작됐지만 host port로 publish하지 않았다. Offline mode는 로컬 재현을 위한 현재 실행조건이며 외부 network에 server port를 공개하지 않는다.
    - [O] 4. 외부 LLM 호출 전 TaskManager·DataManager·Controller 초기화에서 발생하는 source/runtime 오류를 확인한다.
        - VillagerAgent의 제어 평면이 외부 추론이나 Minecraft 행동을 시작하기 전에 Python source와 설치 dependency만으로 생성되는지 확인했다. 검사 대상은 실제 `VillagerBench` virtual environment, 단일 `Alice` 등록, 초기 상태의 `DataManager` 반영, `TaskManager`, `GlobalController`와 controller가 생성하는 단일 `BaseAgent`다. Task decomposition을 시작하는 `TaskManager.init_task()`와 agent action, embedding 및 LLM 요청은 이 단계에 포함하지 않았다.
        - Python 3.10.20 격리환경에서 검사는 exit code 0으로 끝났다. 다음 객체와 역할 연결이 생성됐다.
        | 확인 항목 | 결과 |
        |---|---|
        | `VillagerBench` | `_virtual_debug=True`로 생성하고 `Alice` 및 원본 QuickStart의 tool 11개 등록 |
        | 초기 상태 반영 | 한 agent의 virtual state를 `DataManager.update_database_init()`에 반영 |
        | `TaskManager` | 생성 성공, LLM role `TaskManager` 및 실제 agent tool description 연결 |
        | `DataManager` | 생성 성공, LLM role `DataManager` 연결 |
        | `GlobalController` | 생성 성공, LLM role `GlobalController` 연결 |
        | `BaseAgent` | 실제 `VillagerBench.agent_pool`의 `Alice` 한 명으로 생성 |
        | model client | 현재 기준 문자열 `qwen3-next-80b-a3b-instruct`로 client 객체 생성 |
        | Retriever client | 생성되지 않음; 실제 retrieval 전까지 lazy 상태 유지 |
        | 외부 LLM·embedding·기타 network 요청 | audit 결과 0건 |
        - 이는 **제어 평면 생성자 수준의 import·dependency·객체 연결이 통과했다는 결과**이며, task decomposition, controller assignment, Minecraft action 또는 benchmark 성공을 의미하지 않는다. 향후 Google adapter로 교체한 뒤 동일 검사를 다시 통과해야 provider 변경의 초기화 회귀가 없다고 판단할 수 있다.
        - 실제 네트워크 요청과 API 호출이 없음에도 API 조건을 따지는 경우가 있어서 tmp 폴더에서 해당 문제를 우회하고 실험한 결과 TM AC SM BA 들 초기화 상태는 잘 수행한 것으로 보임. 따라서 우회한 결과를 바탕으로는 4번은 통과
    - [X] 5. 승인된 API credential로 `tiny_start.py`의 한 개 요청을 실행하고 실제 호출·token·latency·오류를 기록한다.
    - [X] 6. 대표 VillagerBench 과제 하나를 단일 configuration으로 실행해 completion score, action log와 token log가 함께 생성되는지 확인한다.
    - [X] 7. 단일 실행이 반복 가능할 때만 batch configuration과 agent 수 변화 실험으로 확장한다.
2) 주요 이슈
    - 외부 LLM API 콜에서 제3자 중개자 API 사용 :
    - 외부 API 통합 및 로컬 모델 교체 : 외부 API는 구글 API 사용으로 결정
    - 현재 연구질문을 떠올리면 '상이한 연산/메모리 능력 -> 적절한 태스크 분배?'인데 OS나 컴퓨터 네트워크 과목에서 다룬 스케줄링/conjestion 관련 문제들과 엮일 가능성이 높다고 직관적으로 생각.
        - 실제 유의미한 연관이 있는지는 추가 조사해야하지만, 일단 무시할 수 없다는 생각.
        - 기존 빌리저 에이전트가 어떤 할당정책을 가져오는지도 한번 논문/코드 둘 다 조사할 필요성
    - 사소한 이슈
        - 내부 주석처리 전부 중국어 : -> 영어로 번역 완료
        - 논문상 명칭과 코드상에서의 명칭 일부 불일치 : TaskManager(task decomposer), GlobalController(agent comtroller), DataManager(state manager) 등 -> 큰 문제는 없고 오히려 뜯어 고치면 문제가 있을 수 있으므로 보류
3) 다음 계획
    - 7번 계획까지 완료 후 본격적인 벤치마크 smoke test
    - villager bench 가 수식으로 어떤걸 정확히 측정하는지, 그리고 appendix에서 아키텍처 알고리즘이나 벤치 알고리즘 조사
        - 추가로 tickingCollabBench 등에서 이질성 측정 부분도 현 villager 벤치에 통합해야하므로 관련 부분 조사 (수식 의미 파악하고 정의를 어떻게 바꿔야 기종간 차이를 측정할 수 있는지)
4) +@ :
    - jev 모델 : 자연어 응답을 줄줄이 생성하는 기존 LLM 모델과 달리 특정 속성에 대한 확률을 매우 빠르고 저렴하게 생성하는 모델. system one 이라고 개발사가 명명. 기존 LLM 모델들과 아키텍처가 어떻게 다른지는 추가 조사 (당연히 현 프로젝트에 이식 여부는 큰 줄기들을 일단 쳐 내고 나중에 선택적 고려)
        - <https://www.youtube.com/watch?v=vj7hysh0mOI&t=5s>
        - in context에서도 내부적으로 긴 자연어 추론이 필요한 경우를 빼면 '과거이력(history)->다음 행동 개선' 과정에 대해 더 간소화되고 저렴한 파이프라인 구축할 가능성도 있음
        - 단, history에서 충분한 정보를 제공하지 못할경우 개선을 띄는데 부족할 가능성도 O
    - 글리치 토큰 : 토크나이저에서의 어휘와 실제 학습되는 corpus간 불일치에서 발생하는 현상. 특정 입력을 넣으면 챗봇이 비정상적인 반응 출력
        - <https://www.youtube.com/watch?v=oUn8m5Ghm94>
        - [거대한 텍스트 corpus] -> Tokenizer 학습 -> Vocabulary 생성{the, cat, ing, HTTP, weird_string_123, ...} -> LLM 학습 -> 각 token의 의미/사용법 학습
            - Glitch token : 비정상적/과소학습된 token representation ; tokenizer·embedding·representation
            - Prompt injection : 공격 명령을 입력에 섞음 ; semantic/instruction layer
            - Hijacking : 모델의 목표·행동을 탈취 ; 전체 control flow
            - 글리치 토큰을 이용해 인젝션 과정에서 원하는 반응을 유도 할 수 있다면 보안상 심각한 위해가 되기 때문에 흥미로운 주제
    - 리눅스 로컬 내에서 실험이나 코드를 돌릴경우 도커를 써서 환경을 격리한 다음에 진행? 혹은 그냥 네이티브 환경에서 진행?

## 9.30 랩미팅

1) 벤치마크 검증 완료 절차
2) 논문의 벤치마크/수식 정리
    - 완수율(Completion rate ; C)
      - $C=\frac{\text{(확인된 식별자)}}{\text{(총 기대 식별자)}}$
      - 식별자 : 진전을 식별 가능한 객체 (블록, 재료, 특정 행동 등)
    - 완료 효율성(Effiency of Completion; E)
      - $E=\frac{\text{(작업 완료율)}}{\text{(작업 처리 시간)}}$
    - 에이전트 활용 밸런스(Balenced agent utilization score; B)
      - 에이전트들에게 과업 분산 측정. active running time이 동등한지?
      - $t' = \frac{t-\min(t)}{\max(t)-\min(t)}$
        - 에이전트 러닝 타임 t에 대한 min-max 정규화
      - $B=1-\sigma(t')$ ; $\sigma()$=시그모이드
    - 블록 배치 뷰 적중률(Block placement view hit rate; VHR) : 다양한 시점에서 건축물의 구조적 온전함, 시각적 통일성을 평가
      - $S_{vhr}= \frac{1}{V} \sum_{v=1}^V \text{IoU}(C_{v(\theta,\phi)},E_{v(\theta,\phi)})$
      - IoU = Jaccard score = $\frac{a\cap b}{a \cup b}$

3) conjestion/스케줄링 관련성 위해 학부 강의 개념 조사
    - 전기전자공학부 박재현 교수님 과목
      1) 컴퓨터 시스템 (OS+컴퓨터구조론) : 중간(컴구), 기말(OS) 둘 다 총정리 필기본 PDF OK
      2) 컴퓨터 네트워크 : 중간 PDF는 O. 기말 PDF를 잃어버림
4) 주요 이슈 & 생각할 만한 지점
    - Villager agent 논문에서도 에이전트 수의 효율에 대한 체감수확 증거 확인
      - 감소 원인 : (1)에이전트간 자원 경쟁, (2)LLM에 의한 관리복잡도 로 추측(논문에서 엄밀하게 조사하진 X)
      - 7페이지 'Agent Collaboration and Performance Dynamics' 섹션, table6
    - 서로 다른 능력간 협업 어려움
      - table 2에, 서로 다른 추가 API를 가진 에이전트로 구성된 팀은 모든 지표에서 더 낮은 성적. -> 능력이 서로 이질적일 때 조정(coordination) 의 복잡성 증가가 원인이라 해석
        - 한 에이전트가 다른 에이전트 작업 완료에 의존하는 경우 전체 워크플로우 발생 -> 병목/작업 실패 가능
      - 효율성 저하와는 별개로 다양한 능력을 갖추는게 작업 환경에 풍부한 복잡성 부여. 보다 복잡한 혁력적 상호작용이 발생할 가능성 부여.
        - 점수 최대화에선 최적 구성 X.
        - 단, 이러한 설정은 벤치마크에서의 고도화된 협력과 전략을 연구하기 좋은 실험 환경이다.
      - 마인스카이넷의 연구질문과 간접적으로 연결되는 지점?
    - 토큰 비용의 트레이드 오프
      - 작업 완료 성능과 토큰 사용량 사이 관계 측정을 위해 token cost 정의.
        - $\text{cost}=\frac{\text{completion tokens}}{\text{score}+\epsilon}+\text{action num}$
          - Completion tokens : 액션 완료에 필요한 평균 토큰
          - action num : 작업 수행중 실행된 유요한 행동의 수
          - 엡실론=1 : score=0일때 분모 0 방지용.
      - VillagerAgent와 비교군 프레임워크인 AgentVerse를 대조 : 행동당 토큰은 더 사용하지만 token cost는 훨씬 낮다
      - 원인
            1) 에이전트별 능력이 상이하면 협업 조정이 어렵. 성능 저하.
                - 단, heterogeneous agent 환경은 복잡한 협업 행동 연구 유용
            2) VA는 액션당 토큰을 더 먹지만 성능 대비 토큰 효율이 더 좋다.
                - 즉, 조금 더 많은 추론 비용 -> 훨씬 높은 테스크 퍼포먼스; 이 지점에서 trade-off 성립한다고 주장.

- 현재 논문에서 확인 가능 지점과 연구 포인트
    1) 이기종 환경에 대한 정당성을 밀어붙여 (특히 이질성 자체가 서로 다른 API이므로 정당성이 약간 더 증가한다 생각) 기존 mineskynet 작업을 지속
    2) 혹은, 에이전트 수 효율성과 작업 실패 부분에 집중하여 conjestion/schduleing 분야에서 개선 접목
  - 에이전트간 추론 이질성을 정의하기가 상당히 난감하다고 생각.
    - 그냥 tickingCollab 논문 끌고 오지 않아도 에이전트별 추론성능+메모리 크기 해서 이걸 지표로 잡으면 되지 않나? 라는 생각이 들지만 어디부터 어디까지 타당한지 모르겠음
  - 한편 2)에도 호기심이 생김 : VA에서의 에이전트 수 효율/ 작업 실패 문제가 OS/넷웍 문제 상황과 구조적으로 유사하다면 1) 보다 상황이 쉬워질수도 있다고 생각.
- 피드백
  - 가능하면 알고리즘 개선/ 방법론 ;단, 논문 추천본은 현상 분석
    - 논문 추천 : <멀티턴 에서 길을 잃는다>
      - 논문 주제 : 긴 컨텍스트에서 맥락을 잃는다. → 근거를 체계적으로 잘 정리;
    - 즉, 논문 나온걸 보는건 O. 연구 과정을 어떻게 했나도 볼 수 있으면 good.
      - 가지치기를 잘하자. 방대함이 있어야하지만 정리도 해야함. 버리는게 어렵다. 다 가져가는건 X.
      - 고민하는건 좋지만 적정 수준 이상이면 X. 계층적으로 정리해서 도출 → 적당히 추리는게 어렵다. 늪같은 구간; 뭘 정리/밀고 나갈까?
      - 논문 쓸때 라우팅 → 참조논문을 조사. OS 분야는 X? 그런데 끌고오면 good.
        - 다른 분야들끼리 접목이 안되는게 서로 질문이 달라서.
  - 게임 화면 녹화/스샷도 고려.

### (9.30 랩미팅 후 추가 질문; 현 연구와 관련 낮음)

- 계량경제 : 이분산성, 내생성?
- 시계열 : stationary? (계절성/time trend X), 가성회귀?, 인과성?
  - 자산 비정상성; 경제학 이론이랑 100% 일치하냐? 는 아닐수도
  -
- 포폴 이론 : efficient frontier에 해당하나? 분산을 다변화할 수 있는가? 손실회피성향?
- 도메인간 충돌 -> 좋은 포지션 X; 기존 권위 & 문제 지적? -> 좋은걸로 인정 X; 내가 고민한게 맞다? 해봐서 안되면 / 잘 안되면 내가 해본게 맞았다.

## 10.7 랩미팅

<!-- ### (optional) 수식/정의/개념 정리 -->

### 진행상황 및 목표

#### 0) [O] 벤치마크에서 controller_tiny.py 대신 controller.py 검증

1) 이미 성공한 Task0·1인을 원본 Controller로 재실행해 기존 결과와 같은 조건에서 완주 여부를 확인
2) 통과하면 앞서 선정한 Task6·3인으로 그래프 생성, 배정, 실행을 확인
3) 각 실행에서 Controller의 직접 배정인지 LLM 배정인지 로그로 구분

#### 1) [O] Construction 중간 규모 시나리오 하나를 2–3개 에이전트로 실행

- 생성된 태스크 그래프에서 실제로 두 작업 이상을 할당할 선택지가 생기는지 확인
- 사용한 Controller 경로와 최종 점수·실행 로그를 함께 기록

#### 2) [->] 병목 또는 할당 실패가 드러나는 조건을 정해 시나리오 실행

- 그래프의 선행관계·할당 후보와 실제 작업 배정을 확인
- 작업별 ready → assigned → start → end 시점, 유휴 에이전트 수를 기록
- 관찰된 지연·실패를 Decomposer·TaskManager·Controller·작업 실행 중 어느 단계에서 발생했는지 구분
- 해당 현상이 관찰되지 않으면 시나리오 조건을 재검토하고 미관찰 결과도 기록

##### Construction 시나리오 비교와 2) 후보 (구조 원본: `data/building_blue_print.json`)

| Task 범위·대표 | 구조상 차이 | 병목 탐색에서의 의미 |
| --- | --- | --- |
| 0–19: 램프·작은 표식·화석 (Task0, Task6) | 3–12블록. Task0은 3층 수직 배치, Task6은 동일 재료·동일 높이 6블록 | Task0은 선행 순서가 강하고, 이미 성공한 Task6은 병렬 배정의 작은 기준점 |
| 20–43: 도로·교차로 중심 (Task20·21, 28·29) | 대체로 12–28블록. 단층에 수평으로 펼쳐진 구조가 많음 | 재료·높이 변수를 줄인 채 작업량과 agent 간 공간 간섭을 단계적으로 늘릴 수 있음 |
| Task25: 이글루 중간 구조 | 15블록·2종 재료·3개 높이. 벽돌 기둥 4개와 사다리 기둥 1개 | actor 없는 TD/AC 1회 프로브에서 TD는 벽돌 기둥 3개(9/15블록)를 간선 0개의 첫 라운드 계획으로 생성했고, AC는 3개를 Alice·Bob·Cindy에게 유효하게 배정했다. 선행제약 병목·할당 실패는 미관찰 |
| 44–56: 다리·천막·농장·큰 화석 (Task44, 50, 55) | 31–41블록. 여러 높이·재료·방향이 섞임 | 배정 실패의 원인이 복합적이므로 첫 탐색에는 부적합 |
| Task50: 천막 구조 (후속 TD/AC 후보) | 35블록·4종 재료·4개 높이. 기둥·측면·지붕으로 나눌 여지가 있음 | 지지부와 상부 설치의 선행관계 및 병렬 배정 가능성을 먼저 actor 없는 계획·할당 프로브로 확인할 후보. 아직 그래프나 병목은 관찰하지 않음 |
| 57–64: 가로등·큰 도로·우물·우리 (Task57, 60·61, 64) | 42–48블록이지만 구조 편차가 큼. Task57은 14종 재료·11층, Task60·61은 단층·단일 재료, Task64는 4종 재료·4층·방향 조건 | 블록 수만으로 난이도나 병렬성을 대표할 수 없음을 보여줌. Task64는 논문 Table 6과 연결되는 후속 확인 사례 |

- **추천 순서:** Task6(기존 기준점) → Task20(개선 후 12/12 완료) → Task25(TD/AC 첫 라운드 검증 완료) → Task50(TD/AC 프로브 후보) → 필요한 경우에만 선행제약이 있는 case의 actor 포함 실행 → Task64(Table 6 연결). Task28·29는 공간 간섭을 별도로 보려는 경우의 대안이다. 처음에는 3인 조건에서 그래프의 간선·ready 작업 수, 후보, 실제 LLM 배정을 확인하고, agent 수 증가는 같은 구조·설정을 고정한 뒤 적용한다.

- **이유와 한계:** Task25의 첫 라운드 9/15블록은 에이전트 수 이하로 부분 계획을 만드는 현 설정의 결과이므로 과제 전체 계획 실패로 단정하지 않는다. 다만 간선 0개여서 선행제약 병목은 시험하지 못했다. Task50은 구조상 지지부→상부 관계를 계획할 가능성이 있지만, 실제 DAG 간선과 할당 선택지가 생성되는지는 검증 전이다. Task64의 agent 수별 지표는 중간 지점 이후 감소하지만, 원인이 Controller인지 작업 병렬성·actor 간섭인지는 Table 6만으로 구별할 수 없다.

#### 3) [->] 관찰된 현상과 직접 연결되는 컴퓨터 시스템 개념 조사

- 작업 선행관계, 준비 작업 대기, 스케줄링과 자원 경합부터 비교
- 네트워크 혼잡 개념과 기말 자료 복구는 관련성이 확인될 때 추가

##### 작업 DAG와 OS 스케줄링의 연결: 문제와 검증 범위

- VillagerAgent의 Decomposer는 subtask 사이의 **선행관계 DAG**를 만들고, Controller는 선행조건을 만족한 ready task를 가용 agent에게 배정한다. OS의 ready queue는 이 중 실행 가능 작업의 대기·선택에 대응하며, 큐가 선형으로 보인다고 DAG 의존관계가 사라지는 것은 아니다.
- [`컴시기말.pdf`](./컴시기말.pdf)의 스케줄링·동기화·교착상태 개념은 배정 지연과 공유 자원 경합을 분석할 실마리다. 그러나 요약본의 CPU 프로세스 스케줄링만으로 **자연어 목표의 DAG 분해·작업 통합**을 설명할 수 없고, 작업 선행관계·공간 간섭·자원 대기 교착상태도 서로 다른 현상이다. 현재 관찰만으로 congestion이나 deadlock을 주장하지 않는다.
- **다음 확인:** 선행 간선이 있는 소규모 건설 과제에서 작업별 `ready → assigned → start → end`와 agent·공간/자원 상태를 기록해 지연을 그래프 병렬성, Controller 할당, actor 실행 중 어디에 귀속할지 판별한다. 이론 검토는 OS 전체보다 **DAG scheduling과 자원 제약 작업 할당**에 우선 집중한다.

##### 그래프 생성 알고리즘

$$
\begin{array}{r l}
& \textbf{Convert Task List to Graph} \\

\\

1: & G \leftarrow (V,E),\; V \leftarrow \emptyset,\; E \leftarrow \emptyset \\

2: & L \leftarrow [N_1,N_2,\ldots,N_n]
\quad \triangleright \text{Input list} \\

3: & \textbf{for } i \leftarrow 1 \textbf{ to } n \textbf{ do} \\

4: & \hspace{1em} V \leftarrow V \cup \{N_i\}
\quad \triangleright \text{Add element as a node} \\

5: & \hspace{1em} \textbf{if } P(N_i) \neq \emptyset \textbf{ then} \\

6: & \hspace{2em} \textbf{for all } p_j \in P(N_i) \textbf{ do} \\

7: & \hspace{3em} E \leftarrow E \cup \{(p_j,N_i)\}
\quad \triangleright \text{Add edges from predecessors} \\

8: & \hspace{2em} \textbf{end for} \\

9: & \hspace{1em} \textbf{else if } i > 1 \textbf{ then} \\

10: & \hspace{2em} \textbf{for all } p_k \in P(N_{i-1}) \textbf{ do} \\

11: & \hspace{3em} E \leftarrow E \cup \{(p_k,N_i)\}
\quad \triangleright \text{Share predecessors with previous element} \\

12: & \hspace{2em} \textbf{end for} \\

13: & \hspace{1em} \textbf{end if} \\

14: & \textbf{end for}
\end{array}
$$

#### 4) 병목이 재현된 경우 개선 아이디어 하나를 도출하고 동일 조건에서 비교 실행

      - 개선 여부와 함께 어떤 단계의 대기·실패가 달라졌는지 확인

#### 5) 대표 실행 하나를 게임 화면 녹화 또는 스크린샷으로 남김

### 주요 이슈 & 생각할 볼만한 문제

- 건설 task6 실패 직후 원본 실험 환경과 동일하지 않은 마크 월드 조건
  - 실제 게임에 접속해보니 기본 월드에 높이가 -60 좌표인 큰 동굴에 시험장이 생성됨
  - 첫 t6 실패가 단순하게 모델이 실패한게 아니라 몹 스폰, 매우 어두운 시야 등의 영향 받았을 가능성
  - 따라서 다음 시험부터 완전한 평지(기본 y좌표 -60), 난이도 peacefull에서 진행
  - 이후 잠정적으로 월드 조건 이슈는 해결

- 첫 건설 task20 에서 과제 실패
  - 로그와 로직을 살펴본 결과 base agent 쪽에서 추론중 토큰 길이 제한과 파싱 문제가 있다는걸 파악. 또한 에이전트 종료 사유도 로그에 포함되지 않은 결함
  - 토큰 길이 제한을 2배(512 -> 1024)로 늘리고 파싱 파일도 수정.
  - 에이전트 종료 사유도 로그에 찍히게끔 수정
  - 그 다음 t20 시험시 통과 판단 O

- DAG 생성시 디컴포저가 과제에 대한 full 그래프를 만드는게 아니라 부분적으로 그래프 생성하고 재피드백
  - ex) t25 그래프 생성시 완전한 배치가 아니라 구조물 일부만 지시하는 노드 3개짜리 (+간선 X) 불완전 그래프
  - 과제 성격(건설/파밍/방탈출)에 따라 필요가 다르긴 하겠지만, TD/AC의 개선안을 분석하기 위해선 굳이 부분적으로 생성할 필요 없다고 판단
  - 또한 불필요한 BA 비용 지출 막기 위해 TD/AC의 각각 계획/할당만 측정할 td_ad_probe.py 생성
  - 추가로 full 그래프 생성 -> 중단/병목 이슈 생겼을 때, 피드백 마다 하위 계획 생성이 아니라,
    - full 그래프 생성 -> 각 vertex별 step을 기록 -> 중단/병목 되었는가? -> 엣지 연결 수정 or 하위 vertex 생성 아이디어?

- Balance 설명 정정 : $\sigma()$ 는 시그모이드가 아닌 표준편차
  - B 지표 의미 : SD(=0~1)가 낮 -> running time 고르게 분배. -> 1-SD : 1에 가까울수록 good

- DAG 검사 코드 추가 : (코덱스 대화 중) 다만 코드상 주의점이 있습니다. Graph.add_edge()는 순환 여부를 검사하지 않습니다. 즉 DAG로 만들겠다는 프롬프트는 있지만, 생성물이 항상 DAG라는 검증은 없습니다. 위상 정렬이나 임계경로 분석에 앞서 순환 검사를 넣어야 합니다. 또 최근 Task20의 세 작업 그래프는 엣지가 0개여서, 그 실행은 선행제약보다 배정·actor 실행을 관찰한 사례입니다.
  - 일단 BFS나 크루스칼 (혹은 이 방법이 아니더라도) DAG 검사를 해야할 필요

- 교과서별 DAG 문제상황
  - DAG가 데이터를 다루는 핵심 자료구조이므로, DAG 자체에 대한 이해 + DAG와 관련된 연산/특징/thorem 파악 + DAG에서 알려진 문제 -> 해결책 있으면 손쉽게 해결 가능 하다고 판단해 추가 자료 조사
  - all of statistics : 복잡한 인과관계를 띄는 확률 변수/사건들(마르코프 과정?) -> DAG로 표기(인과는 엣지, 확변은 노드) ->
    1) Q1 : 내부의 각 vertex인 확률 변수들을 추정할수 있나?
    2) Q2 : 주어진 데이터[V1, ..., Vn]과 분포 f가 있을 때, 그래프 구조 자체를 추정할 수 있나?
    - (단, 이마저도 자세하기 알려주기보단, DAG 챕터가 DAG 소개/정의들로 구성. 추정법은 위 두 질문에대한 핵심 아이디어만 간단히 소개)
  - Introduction to algoritm : 각 가중치가 존재하는 DAG에서,
    1) 순환이 없는 트리를 최소비용으로 만들 수 있나? (크루스칼 알고리즘)
    2) 출발점 있을때 각 정점까지 최소비용/최단경를 찾을 수 있나? (다익스트라)

- DAG 관련 아이디어
  1) DAG 자료구조를 써야한다는건 명백.
  2) AOS의 마르코프 과정도 선험적으로 각 확률을 그냥 배정해버릴수도 없고 난감함
  3) 다만 선형 큐가 아닌 DAG에서 병목/충돌/대기 문제가 있을 때 OS 기법을 어떻게 써야할지?
  4) 멀티프로세싱/멀티스레딩 관련 조사해서 OS가 cpu에게 어떻게 작업을 병렬 할당 -> 통합 시키는지 조사할 필요

### 다음 계획
