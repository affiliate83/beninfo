"""저장된 application_end_date 값 샘플 확인"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import requests
from requests.auth import HTTPBasicAuth

WP_URL = os.getenv("WP_URL", "").rstrip("/")
WP_USERNAME = os.getenv("WP_USERNAME", "")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD", "")

resp = requests.get(
    f"{WP_URL}/wp-json/wp/v2/policy",
    params={"per_page": 20, "_fields": "id,title,meta"},
    auth=HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD),
    timeout=15,
)
posts = resp.json()
print(f"총 {len(posts)}건 확인")
for p in posts:
    date_val = p.get("meta", {}).get("application_end_date", "(없음)")
    print(f"  [{p['id']}] {p['title']['rendered'][:30]:<30} → {date_val!r}")