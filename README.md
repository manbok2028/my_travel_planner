# 국내 여행지 추천 프로그램 (진행 중)

Gemini API와 Kakao Local API를 조합해서, 날짜를 입력하면 여행하기 좋은 국내 도시와
그 지역 맛집을 추천해주는 CLI 프로그램입니다.

## 현재 진행 상황

* \[x] API 키 발급 (Gemini, Kakao Local)
* \[x] .env로 키 관리
* \[x] Gemini API 호출 + JSON 형식으로 응답 받기
* \[x] Kakao Local API로 맛집 검색
* \[x] 두 API 연결 (Gemini가 추천한 도시로 Kakao 검색어 자동 구성)
* \[x] argparse로 --date 입력받기 + 날짜 형식 검증
* \[ ] 검색 결과 0건 처리 로직 (기본 카운트 메시지는 구현, "데이터 없음" 리포트 표기는 예정)
* \[ ] results/ 폴더에 JSON, Markdown 리포트 저장
* \[ ] 최종 README 완성 (지금 이 파일은 중간 정리본)

## 실행 방법

```bash
pip install python-dotenv requests
python step6.py --date 2026-03-15
```

## API 키 설정 방법

1. 프로젝트 루트에 `.env` 파일을 만듭니다 (`.env.example` 참고)
2. 아래 두 줄을 본인의 실제 키 값으로 채웁니다.

```
GEMINI\_API\_KEY=본인의\_Gemini\_키
KAKAO\_REST\_API\_KEY=본인의\_Kakao\_REST\_API\_키
```

* Gemini 키는 [Google AI Studio](https://aistudio.google.com)에서 무료로 발급받을 수 있습니다.
* Kakao REST API 키는 [Kakao Developers](https://developers.kakao.com)에서 발급받고,
앱 설정에서 **카카오맵(로컬 검색) 사용 설정을 ON**으로 켜야 정상 작동합니다.

## 주의 사항

* `.env` 파일은 절대 GitHub에 올리지 마세요. (`.gitignore`에 포함되어 있습니다)
* API 키가 실수로 노출되면 즉시 재발급(rotate)하세요.

