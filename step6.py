from dotenv import load_dotenv
import os
import requests
import json
import argparse
from datetime import datetime

load_dotenv()

gemini_key = os.getenv("GEMINI_API_KEY")
kakao_key = os.getenv("KAKAO_REST_API_KEY")

# ---- 0) CLI 인자 처리 + 날짜 형식 검증 ----

parser = argparse.ArgumentParser()
parser.add_argument("--date", required=True)
args = parser.parse_args()

try:
    datetime.strptime(args.date, "%Y-%m-%d")
except ValueError:
    print("날짜 형식이 올바르지 않습니다. 예: --date 2026-03-15")
    exit()

# ---- 1) Gemini에게 도시 추천받기 ----

headers = {
    "Content-Type": "application/json"
}

prompt = f"""{args.date}에 여행하기 좋은 국내 도시를 추천해줘.

반드시 아래 JSON 형식으로만 답변해. 다른 설명이나 마크다운 코드블록 없이, JSON 텍스트만 출력해.

{{
  "recommended_city": "도시 이름",
  "weather": "해당 시기 일반적 날씨 요약",
  "events": ["행사1", "행사2"],
  "reason": "추천 이유 2~4문장"
}}
"""

payload = {
    "contents": [
        {"parts": [{"text": prompt}]}
    ]
}

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent?key={gemini_key}"

response = requests.post(url, headers=headers, json=payload)

print(response.status_code)
data = response.json()
answer_text = data['candidates'][0]['content']['parts'][0]['text']
print(answer_text)

parsed = json.loads(answer_text)
print(parsed["recommended_city"])

# ---- 2) 추천받은 도시로 Kakao 맛집 검색하기 ----

places_headers = {
    "Authorization": f"KakaoAK {kakao_key}"
}

places_url = "https://dapi.kakao.com/v2/local/search/keyword.json"
places_params = {
    "query": parsed["recommended_city"] + " 맛집"
}

places_response = requests.get(places_url, headers=places_headers, params=places_params)

print(places_response.status_code)
places_data = places_response.json()

if len(places_data["documents"]) == 0:
    print("맛집 검색 결과가 없습니다.")
else:
    print(f"{len(places_data['documents'])}곳의 맛집을 찾았습니다.")
