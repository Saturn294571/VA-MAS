# Pipeline 작업 지침

## 이 디렉터리의 책임

VillagerAgent의 제어 흐름을 구현한다. `task_manager.py`는 하위 작업·후보를 만들고, `controller.py`는 실행 가능한 작업을 배정하며, `data_manager.py`는 공유 상태를 제공하고, `agent.py`는 배정된 작업을 실행한다. 공통 연구·보안·검증 원칙은 루트 [AGENTS.md](../AGENTS.md)를 따른다.

## 이 디렉터리만의 규칙

- Task Manager가 만든 후보 제약과 Controller의 실제 선택을 별도 단계로 기록한다. 직접 배정인지 LLM 배정인지 로그에서 구분 가능해야 한다.
- 배정 전에 predecessor 완료, task 상태, candidate, 필요 agent 수와 가용성을 확인한다. 잘못된 LLM 응답을 유효 배정이나 성공으로 자동 보정하지 않는다.
- Base Agent의 reflection은 다음 계획에 주는 피드백이다. 최종 benchmark score는 `env/` judger가 판정하므로 이 계층에서 대체하지 않는다.
- TD·AC·actor 시간을 분리할 수 있도록 작업 생성, ready, 배정, 실행 시작·종료와 상태 반영 시점을 연결한다. 실패·재시도·종료 이유도 남긴다.
- `TaskManager` 초기화는 생성 그래프와 로그를 지울 수 있다. 기존 실행 증거가 필요한지 확인하고 프로브·테스트는 격리된 작업 경로에서 수행한다.
- 배정 정책을 바꿀 때는 기존 정책을 재현 가능한 기준선으로 남기고, 새 정책의 선택·설정을 명시한다. 모델 공급자별 인증·응답 처리는 `model/`, Minecraft 행동·최종 채점은 `env/`에 둔다.
