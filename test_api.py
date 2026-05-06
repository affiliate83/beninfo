import os
import requests
from lxml import etree
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("DATA_GO_KR_API_KEY")

url = "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001/NationalWelfaredetailedV001"
params = {
    "serviceKey": API_KEY,
    "servId": "WLF00000023",
}

res = requests.get(url, params=params, timeout=15)
root = etree.fromstring(res.content)

print("=== 상세 API 전체 필드 ===")
detail = root.find(".//servDtlInfo")
if detail is None:
    print("servDtlInfo 없음, 루트 구조:")
    for c in root:
        print(f"  {c.tag}: {c.text[:80] if c.text else '(없음)'}")
else:
    for child in detail:
        val = child.text.strip() if child.text else "(없음)"
        print(f"  {child.tag}: {val[:150]}")