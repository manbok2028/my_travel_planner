"""
국내 여행지 추천 프로그램

날짜(--date)를 입력받아,
1) Gemini API로 여행하기 좋은 도시를 추천받고
2) Kakao Local API로 그 도시의 맛집을 검색한 뒤
3) Gemini API로 최종 여행 리포트(Markdown)를 생성해서
results/ 폴더에 원본 JSON과 리포트를 저장한다.
"""

import argparse
import json
import os
import sys
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
KAKAO_REST_API_KEY = os.getenv("KAKAO_REST_API_KEY")

GEMINI_MODEL = "gemini-flash-latest"
GEMINI_URL = (
    f"https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
)
KAKAO_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"


# ---------------------------------------------------------------------------
# 0) CLI 인자 처리 + 날짜 검증 + API 키 확인
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="날짜를 입력하면 국내 여행지와 맛집을 추천해주는 프로그램"
    )
    parser.add_argument("--date", required=True, help="여행 날짜 (형식: YYYY-MM-DD)")
    args = parser.parse_args()

    try:
        datetime.strptime(args.date, "%Y-%m-%d")
    except ValueError:
        parser.print_usage()
        print('오류: 날짜 형식이 올바르지 않습니다. 예) --date "2026-03-15"')
        sys.exit(1)

    return args.date


def check_api_keys():
    missing = []
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    if not KAKAO_REST_API_KEY:
        missing.append("KAKAO_REST_API_KEY")

    if missing:
        print(f"오류: 다음 API 키가 설정되지 않았습니다: {', '.join(missing)}")
        print("프로젝트 루트에 .env 파일을 만들고 아래 형식으로 키를 넣어주세요:")
        print("  GEMINI_API_KEY=발급받은_키")
        print("  KAKAO_REST_API_KEY=발급받은_키")
        print("(.env.example 파일을 참고하세요)")
        sys.exit(1)


# ---------------------------------------------------------------------------
# 1) LLM 연동 - 1차 추천 (날씨/행사 정보, JSON)
# ---------------------------------------------------------------------------

def call_gemini(prompt: str) -> str:
    """Gemini API를 호출해서 텍스트 응답을 반환한다. 실패 시 예외를 던진다."""
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    response = requests.post(GEMINI_URL, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    data = response.json()
    return data["candidates"][0]["content"]["parts"][0]["text"]


def get_recommendation(date: str, errors: list) -> dict | None:
    """1차 추천 JSON을 받아온다. 파싱 실패 시 1회만 재시도한다."""
    base_prompt = f"""{date}에 여행하기 좋은 국내 도시를 하나 추천해줘.

반드시 아래 JSON 형식으로만 답변해. 다른 설명이나 마크다운 코드블록 없이, JSON 텍스트만 출력해.

{{
  "recommended_city": "도시 이름",
  "weather": "해당 시기 일반적 날씨 요약",
  "events": ["행사 후보1", "행사 후보2"],
  "reason": "추천 근거 2~4문장"
}}
"""

    retry_prompt = """방금 응답을 JSON으로 파싱하지 못했습니다.
아래 키만 포함한 순수 JSON 텍스트만 다시 출력해줘. 설명, 코드블록 없이 JSON만 출력해.

{
  "recommended_city": "...",
  "weather": "...",
  "events": ["...", "..."],
  "reason": "..."
}
"""

    for attempt, prompt in enumerate([base_prompt, retry_prompt], start=1):
        try:
            text = call_gemini(prompt)
        except requests.exceptions.RequestException as e:
            errors.append({
                "step": "llm_recommendation",
                "type": "REQUEST_ERROR",
                "message": str(e),
            })
            return None
        except (KeyError, IndexError) as e:
            errors.append({
                "step": "llm_recommendation",
                "type": "RESPONSE_FORMAT_ERROR",
                "message": str(e),
            })
            return None

        # 마크다운 코드블록으로 감싸져 오는 경우 대비
        cleaned = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            errors.append({
                "step": "llm_recommendation",
                "type": "JSON_PARSE_ERROR",
                "message": f"{attempt}차 시도 파싱 실패",
            })
            continue

    return None


# ---------------------------------------------------------------------------
# 2) 지도/장소 검색 API 연동 - 맛집 검색
# ---------------------------------------------------------------------------

def search_places(city: str, errors: list) -> list:
    """Kakao Local API로 맛집을 검색한다. 실패/0건이어도 프로그램은 계속 진행한다."""
    headers = {"Authorization": f"KakaoAK {KAKAO_REST_API_KEY}"}
    params = {"query": f"{city} 맛집", "size": 5}

    try:
        response = requests.get(KAKAO_URL, headers=headers, params=params, timeout=15)
    except requests.exceptions.RequestException as e:
        errors.append({"step": "place_search", "type": "NETWORK_ERROR", "message": str(e)})
        return []

    if response.status_code in (401, 403):
        errors.append({
            "step": "place_search",
            "type": "AUTH_ERROR",
            "message": f"HTTP {response.status_code}",
        })
        return []

    if response.status_code != 200:
        errors.append({
            "step": "place_search",
            "type": "HTTP_ERROR",
            "message": f"HTTP {response.status_code}",
        })
        return []

    documents = response.json().get("documents", [])

    if not documents:
        errors.append({
            "step": "place_search",
            "type": "EMPTY_RESULT",
            "message": f"0 results for query={city} 맛집",
        })
        return []

    places = []
    for doc in documents:
        places.append({
            "name": doc.get("place_name"),
            "address": doc.get("road_address_name") or doc.get("address_name"),
            "category": doc.get("category_name"),
            "url": doc.get("place_url"),
            "x": doc.get("x"),
            "y": doc.get("y"),
        })
    return places


# ---------------------------------------------------------------------------
# 3) LLM 연동 - 최종 리포트 생성 (Markdown)
# ---------------------------------------------------------------------------

def generate_report(date: str, recommendation: dict | None, places: list, errors: list) -> str:
    """1차 추천 + 맛집 목록을 바탕으로 최종 Markdown 리포트를 LLM으로 생성한다."""
    if recommendation is None:
        recommendation = {
            "recommended_city": "정보 없음",
            "weather": "정보 없음",
            "events": [],
            "reason": "1차 추천 정보를 가져오지 못했습니다.",
        }

    places_text = "데이터 없음" if not places else "\n".join(
        f"- {p['name']} ({p.get('category', '')}) - {p.get('address', '')}"
        for p in places
    )

    events_text = ", ".join(recommendation.get("events") or []) or "없음"

    prompt = f"""아래 정보를 바탕으로 {date} 국내 여행 추천 리포트를 Markdown으로 작성해줘.

추천 지역: {recommendation.get('recommended_city')}
추천 이유: {recommendation.get('reason')}
날씨 요약: {recommendation.get('weather')}
행사/축제: {events_text}
맛집 목록:
{places_text}

리포트에는 아래 섹션을 이 순서대로, ## 헤더를 사용해서 포함해줘:
## 추천 지역
## 추천 이유
## 날씨 요약
## 행사/축제
## 맛집 추천
## 1일 일정 제안 (오전/오후/저녁 수준으로)

맛집 목록이 "데이터 없음"이면 맛집 추천 섹션에도 "데이터 없음"이라고 그대로 표기해줘.
다른 설명 없이 Markdown 본문만 출력해줘 (코드블록으로 감싸지 마).
"""

    try:
        report_body = call_gemini(prompt).strip()
        report_body = report_body.removeprefix("```markdown").removeprefix("```").removesuffix("```").strip()
    except (requests.exceptions.RequestException, KeyError, IndexError) as e:
        errors.append({"step": "report_generation", "type": "REQUEST_ERROR", "message": str(e)})
        # LLM 호출이 실패해도 최소한의 리포트는 직접 구성해서 진행한다
        report_body = (
            f"## 추천 지역\n{recommendation.get('recommended_city')}\n\n"
            f"## 추천 이유\n{recommendation.get('reason')}\n\n"
            f"## 날씨 요약\n{recommendation.get('weather')}\n\n"
            f"## 행사/축제\n{events_text}\n\n"
            f"## 맛집 추천\n{places_text}\n\n"
            f"## 1일 일정 제안\n데이터 없음 (리포트 자동 생성 실패)"
        )

    header = f"# {date} 국내 여행 추천 리포트\n\n"
    if errors:
        errors_lines = "\n".join(f"- [{e['step']}] {e['type']}: {e['message']}" for e in errors)
    else:
        errors_lines = "없음"
    errors_section = f"\n\n## 오류 요약(errors)\n{errors_lines}\n"

    return header + report_body + errors_section


# ---------------------------------------------------------------------------
# 4) 결과 저장
# ---------------------------------------------------------------------------

def save_results(date: str, recommendation: dict | None, places: list, errors: list, report_md: str):
    os.makedirs("results", exist_ok=True)

    raw_data = {
        "recommendation": recommendation,
        "places": places,
        "errors": errors,
    }
    json_path = os.path.join("results", f"{date}_data.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2)

    md_path = os.path.join("results", f"{date}_travel_plan.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    return json_path, md_path


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    date = parse_args()
    check_api_keys()
    errors: list = []

    json_path = os.path.join("results", f"{date}_data.json")

    # 보너스: 같은 날짜로 재실행 시, 저장된 원본 JSON이 있으면 API 호출을 건너뛴다
    cached = None
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
        except (json.JSONDecodeError, OSError):
            cached = None

    if cached:
        print("[1-2/3] 캐시된 결과를 발견했습니다. API 호출을 건너뜁니다.")
        recommendation = cached.get("recommendation")
        places = cached.get("places", [])
        errors = cached.get("errors", [])
        if recommendation:
            print(f'    - recommended_city: "{recommendation.get("recommended_city")}"')
    else:
        print("[1/3] 1차 추천 생성 중(LLM)...")
        recommendation = get_recommendation(date, errors)
        if recommendation:
            print(f'    - recommended_city: "{recommendation.get("recommended_city")}"')
        else:
            print("    - 1차 추천 실패, 기본값으로 진행합니다.")

        print("[2/3] 맛집 검색 중(지도/장소 API)...")
        city = recommendation["recommended_city"] if recommendation else date
        places = search_places(city, errors)
        if places:
            print(f"    - 맛집 {len(places)}곳 검색 완료")
        else:
            print("    - 검색 결과 없음, '데이터 없음'으로 진행합니다.")

    print("[3/3] 최종 리포트 생성 중(LLM)...")
    report_md = generate_report(date, recommendation, places, errors)
    print("    - 리포트 생성 완료")

    _, md_path = save_results(date, recommendation, places, errors, report_md)
    print(f"\n완료! {md_path} 를 확인하세요.")


if __name__ == "__main__":
    main()
