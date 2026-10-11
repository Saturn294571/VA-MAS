# Minecraft 환경·평가 지침

## 이 디렉터리의 책임

Minecraft 연결·Mineflayer 행동 API, `VillagerBench` 수명주기와 Construction/Farming/Escape judger의 환경 기반 평가를 담당한다. 공통 규칙은 루트 [AGENTS.md](../AGENTS.md)를 따른다.

## 이 디렉터리만의 규칙

- actor의 성공 메시지와 서버의 실제 block·inventory 상태를 구분한다. judger 점수나 행동 피드백을 바꿀 때 실제 월드 상태와 전후 로그로 검증한다.
- 월드 종류, 난이도, 스폰, Minecraft 버전, bot 권한과 judger 설정을 실험 조건으로 기록한다. 다른 조건의 점수를 동일한 반복으로 합치지 않는다.
- `VillagerBench` 생성·종료와 judger 스크립트는 파일 초기화, 서버 접속, bot 생성 같은 부작용을 가질 수 있다. 단순 import나 오프라인 검사로도 해당 경로가 실행되는지 확인하고 기존 로그·월드를 보호한다.
- 환경 준비·관리자 명령은 서버 호스트의 통제 경로에 두고 일반 actor의 행동 API와 섞지 않는다. 기존 OP·서버 권한을 임의로 바꾸지 않는다.
- 하위 작업의 분해·agent 배정은 `pipeline/`, 모델 인증·호출은 `model/`의 책임이다. 이 디렉터리에는 benchmark 환경과 판정 근거만 둔다.
