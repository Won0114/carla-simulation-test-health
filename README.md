# CARLA Simulation Test Health

공개 CARLA Leaderboard JSON 결과를 검증하고 SQLite에 저장한 뒤, 테스트 건강 상태와 release 회귀를 분석하는 Python 프로젝트입니다. Streamlit 대시보드에서 완료율, 점수, 실행 시간, 반복 위반 및 조사 대상 경로를 확인할 수 있습니다.

## 주요 기능

- CARLA JSON 구조 및 자료형 검증
- 여러 JSON을 중단 없이 처리하는 batch import
- SHA-256 기반 중복 방지
- SQLite 정규화 저장
- 완료율, 평균 점수, 평균 및 p95 실행 시간 계산
- 반복 위반 및 critical infraction 탐지
- baseline과 candidate release 회귀 비교
- CLI와 Streamlit 대시보드
- unit/integration test와 GitHub Actions CI

## 구조

```text
CARLA JSON
    ↓
carla_parser.py       검증 및 RouteResult 변환
    ↓
importer.py           폴더 단위 batch 처리
    ↓
database.py           SQLite 저장 및 조회
    ↓
health.py             SLO와 반복 문제 분석
    ↓
comparison.py         release 회귀 비교
    ↓
cli.py / dashboard.py CLI 및 시각화
```

## 설치

Python 3.10 이상이 필요합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

## 사용법

샘플 JSON 구조 확인:

```bash
carla-health inspect data/raw/679_0_0_result.json
```

한 release의 JSON 폴더를 import:

```bash
carla-health import --directory data/raw --release public-sample
```

전체 또는 release별 health report:

```bash
carla-health report
carla-health report --release public-sample
```

두 release 비교:

```bash
carla-health compare --baseline release-v1 --candidate release-v2
```

비교하려면 각 버전의 JSON을 서로 다른 폴더에서 release 이름과 함께 먼저 import합니다.

```bash
carla-health import --directory results/release-v1 --release release-v1
carla-health import --directory results/release-v2 --release release-v2
```

대시보드 실행:

```bash
streamlit run dashboard.py
```

브라우저에서 `http://localhost:8501`을 엽니다.

## 기본 SLO

| 지표 | 목표 |
|---|---:|
| Route completion | 95% 이상 |
| Average composed score | 80 이상 |
| p95 system duration | 600초 이하 |
| Critical infractions | 0 |

Critical infraction에는 충돌, 신호 위반, 경로 이탈 및 타임아웃이 포함됩니다. 같은 위반이 두 번 이상 나타나면 recurring infraction 경고가 발생합니다.

## 테스트

```bash
python -m unittest discover -s tests -v
```

## 샘플 데이터

저장소에는 서로 다른 시나리오의 공개 결과 3개가 포함됩니다. 상세 출처와 링크는 [`data/raw/README.md`](data/raw/README.md)에 기록되어 있습니다. 샘플은 parser 및 분석 흐름 시연용이며, 실제 release 판단에는 동일한 테스트 구성으로 생성한 여러 버전의 결과를 사용해야 합니다.
