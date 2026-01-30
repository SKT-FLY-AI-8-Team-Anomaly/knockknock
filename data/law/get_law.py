import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

# 스크립트/상위 폴더에서 .env 로드
for _d in [Path(__file__).resolve().parent, Path(__file__).resolve().parents[1]]:
    _e = _d / ".env"
    if _e.exists():
        load_dotenv(_e)
        break
else:
    load_dotenv()

BASE_URL = "https://www.law.go.kr/DRF"
OC = os.getenv("LAW_OC") or os.getenv("OC")
if not OC:
    raise RuntimeError(".env에 LAW_OC(또는 OC)를 설정하세요. 예: LAW_OC=hyein1543")
HEADERS = {"User-Agent": "law-collector"}

QUERIES = [
    # QUERIES를 입력하여 관련 법령을 찾습니다.
]

def search_laws(query, page=1, display=100):
    """현행법령(시행일) 목록 조회"""
    url = f"{BASE_URL}/lawSearch.do"
    params = {
        "OC": OC,
        "target": "eflaw",
        "type": "JSON",
        "query": query,
        "nw": 3,            # 현행만
        "display": display,
        "page": page,
    }
    res = requests.get(url, params=params, headers=HEADERS, timeout=10)
    res.raise_for_status()
    return res.json()

def collect_law_ids():
    """여러 query로 법령 ID / MST 수집"""
    law_map = dict()  # key: 법령ID, value: 메타정보

    for q in QUERIES:
        print(f"🔍 검색어: {q}")
        page = 1

        while True:
            data = search_laws(q, page)
            laws = data.get("LawSearch", {}).get("law", [])
            if not laws:
                break

            for law in laws:
                law_id = law.get("법령ID")
                law_map[law_id] = {
                    "법령ID": law_id,
                    "법령명": law.get("법령명한글"),
                    "MST": law.get("법령일련번호"),
                    "시행일자": law.get("시행일자"),
                    "소관부처": law.get("소관부처명"),
                }

            total = int(data["LawSearch"]["totalCnt"])
            if page * 100 >= total:
                break

            page += 1
            time.sleep(0.2)  # 서버 배려

    return law_map

def fetch_law_body_by_id(law_id):
    """현행법령 본문 조회 (ID 기준)"""
    url = f"{BASE_URL}/lawService.do"
    params = {
        "OC": OC,
        "target": "eflaw",
        "type": "JSON",
        "ID": law_id,
    }
    res = requests.get(url, params=params, headers=HEADERS, timeout=10)
    res.raise_for_status()
    return res.json()

def main():
    # 1️⃣ 법령 식별자 수집
    law_map = collect_law_ids()
    print(f"\n✅ 수집된 법령 수: {len(law_map)}")

    # 2️⃣ 법령 본문 수집
    all_laws = {}

    for law_id, meta in law_map.items():
        print(f"📘 조문 수집 중: {meta['법령명']}")
        try:
            body = fetch_law_body_by_id(law_id)
            all_laws[law_id] = {
                "meta": meta,
                "body": body,
            }
            time.sleep(0.2)
        except Exception as e:
            print(f"❌ 실패: {law_id}", e)

    print(f"\n🎉 최종 수집 완료: {len(all_laws)}개 법령")
    return all_laws

if __name__ == "__main__":
    laws = main()
    out_path = Path(__file__).resolve().parent / "law_data.json"
    out_path.write_text(json.dumps(laws, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"저장 완료: {out_path}")
