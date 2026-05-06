import os
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

WP_URL = os.getenv("WP_URL", "").rstrip("/")
USERNAME = os.getenv("WP_USERNAME", "")
PASSWORD = os.getenv("WP_APP_PASSWORD", "")

print(f"URL: {WP_URL}")
print(f"Username: {USERNAME}")

# 현재 로그인된 사용자 확인
resp = requests.get(
    f"{WP_URL}/wp-json/wp/v2/users/me",
    auth=HTTPBasicAuth(USERNAME, PASSWORD),
    timeout=10,
)
print(f"\n상태코드: {resp.status_code}")
print(f"응답: {resp.text[:500]}")