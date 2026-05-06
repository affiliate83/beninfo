"""API 상세 응답 원문 확인"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import requests
from lxml import etree

API_KEY = os.getenv("DATA_GO_KR_API_KEY")
BASE = "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001"

# 목록에서 서비스 ID 하나 가져오기
r = requests.get(f"{BASE}/NationalWelfarelistV001",
    params={"serviceKey": API_KEY, "srchKeyCode": "001", "pageNo": 1, "numOfRows": 1},
    timeout=15)
root = etree.fromstring(r.content)
item = root.find(".//servList")
serv_id = item.findtext("servId", "").strip()
serv_nm = item.findtext("servNm", "").strip()
print(f"서비스: {serv_nm} ({serv_id})")

print("\n목록 API 날짜 관련 필드:")
for el in item:
    if el.text and el.text.strip():
        tag = el.tag.lower()
        if any(k in tag for k in ["dt", "date", "end", "begin", "bgng", "apply", "aply", "term", "period"]):
            print(f"  {el.tag}: {el.text.strip()}")

print("\n상세 API 원문 (처음 2000자):")
import time; time.sleep(2)
r2 = requests.get(f"{BASE}/NationalWelfaredetailedV001",
    params={"serviceKey": API_KEY, "callTp": "D", "servId": serv_id},
    timeout=15)
print(f"  status: {r2.status_code}")
print(r2.text[:2000])