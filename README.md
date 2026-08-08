# 국내 여행지 추천 프로그램

날짜를 입력하면 Gemini API가 여행하기 좋은 국내 도시를 추천하고,
Kakao Local API로 그 지역 맛집을 검색한 뒤, 최종 여행 리포트를 생성하는 CLI 프로그램입니다.

## 개요

1. `--date`로 입력받은 날짜를 Gemini API에 보내 도시/날씨/행사 정보를 JSON으로 추천받습니다.
2. 추천받은 도시명으로 Kakao Local API에 맛집을 검색합니다 (최대 5곳).
3. 두 결과를 종합해 Gemini API로 최종 Markdown 리포트를 생성합니다.
4. 원본 데이터(JSON)와 리포트(Markdown)를 `results/` 폴더에 저장합니다.

## 사용된 API

- **LLM API**: Google Gemini (`gemini-flash-latest`)
- **지도/장소 검색 API**: Kakao Local (키워드 검색)

## 실행 방법

### 1) 패키지 설치

```bash
pip install python-dotenv requests
```

### 2) API 키 설정

프로젝트 루트에 `.env` 파일을 만들고 (`.env.example` 참고), 아래 두 줄을 본인의 실제 키로 채웁니다.

```
GEMINI_API_KEY=본인의_Gemini_API_키
KAKAO_REST_API_KEY=본인의_Kakao_REST_API_키
```

- **Gemini 키 발급**: [Google AI Studio](https://aistudio.google.com) → API keys → Create API key (무료)
- **Kakao 키 발급**: [Kakao Developers](https://developers.kakao.com) → 내 애플리케이션 → REST API 키 확인
  - ⚠️ 앱 설정에서 **카카오맵(로컬 검색) 사용 설정을 반드시 ON**으로 켜야 정상 작동합니다.

### 3) 실행

```bash
python travel_planner.py --date "2026-03-15"
```

날짜 형식이 잘못되면 사용법을 출력하고 즉시 종료합니다.

### 4) 결과 확인

실행이 끝나면 `results/` 폴더에 아래 파일이 생성됩니다.

- `results/{날짜}_data.json` — 1차 추천 결과 + 맛집 검색 결과 + 오류 요약 원본 데이터
- `results/{날짜}_travel_plan.md` — 최종 여행 리포트 (추천 지역, 날씨, 행사, 맛집, 1일 일정, 오류 요약 포함)

같은 날짜로 다시 실행하면, 저장된 JSON이 있을 경우 API 호출 없이 리포트만 재생성합니다 (비용/속도 절약).

## 에러 처리 정책

- API 키가 하나라도 설정되지 않으면 즉시 종료하고 설정 방법을 안내합니다.
- 지도/장소 API가 실패(네트워크/인증/쿼터 등)하거나 검색 결과가 0건이어도 프로그램은 중단되지 않고, 맛집 섹션을 "데이터 없음"으로 표기한 채 리포트 생성을 계속 진행합니다.
- LLM 응답이 JSON으로 파싱되지 않으면 더 엄격한 프롬프트로 1회만 재시도합니다.
- 위 실패들은 내부적으로 `errors` 리스트에 기록되어, 최종 JSON과 리포트의 "오류 요약" 섹션에 함께 남습니다.

## 보안 주의사항 (API 키 관리)

- API 키는 코드에 직접 작성하지 않고 `.env` 파일(환경변수)로 관리합니다.
- `.env` 파일은 `.gitignore`에 포함되어 있어 Git/GitHub에 올라가지 않습니다.
- 저장소에는 실제 값이 없는 `.env.example`만 포함됩니다. 이 프로그램을 실행하려는 사람은 `.env.example`을 복사해서 `.env`로 이름을 바꾸고, 본인이 발급받은 키를 채워 넣어야 합니다.
- 결과 파일(`results/`)이나 이 README에도 실제 키 값은 포함되지 않습니다.
- 만약 API 키가 실수로 화면 캡처, 로그, 커밋 등에 노출됐다면 즉시 발급처(Google AI Studio / Kakao Developers)에서 키를 재발급(rotate)하세요.

## 개발 환경

- Python 3.10 이상
- 터미널에서 실행 (별도 웹 UI 없음)
