# Benchmark 데이터 지침

## 이 디렉터리의 책임

건설 blueprints, farming 설정, recipe 등 입력 자산과 VA가 실행 중 기록하는 JSON 상태가 함께 있는 폴더다. 공통 규칙은 루트 [AGENTS.md](../AGENTS.md)를 따른다.

## 이 디렉터리만의 규칙

- `building_blue_print.json`, `farm_blue_print.json`, `blueprint_description_all.json`처럼 과제 정의·레시피로 쓰는 입력은 benchmark 조건이다. 변경 시 과제 ID, block·recipe, judger와 기존 결과의 호환성을 확인하고 변경 전후 실행을 분리한다.
- `score.json`, `tokens.json`, `action_log.json`, `history/` 등 실행 중 생성되는 파일은 원시 증거다. 재실행·초기화 전에 필요한 기록을 실행별 `result/`에 보존하고 다른 run의 파일을 덮어쓰지 않는다.
- 데이터 구조를 바꿀 때는 이를 읽는 `env/` judger와 `pipeline/` 소비자 양쪽을 확인한다. 판정을 유리하게 만들려고 blueprint나 score를 사후 수정하지 않는다.
- API 키, 비공개 인증 정보와 개인 데이터를 입력 자산 또는 실험 결과에 넣지 않는다.
