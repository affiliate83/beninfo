"""
마감일이 지난 policy 포스트를 자동으로 비공개(draft) 처리.
매일 GitHub Actions에서 실행.
"""
import os
import sys
import time
from datetime import date
import requests
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv

load_dotenv()

WP_URL  = os.getenv("WP_URL", "").rstrip("/")
WP_USER = os.getenv("WP_USERNAME", "")
WP_PASS = os.getenv("WP_APP_PASSWORD", "")
AUTH    = HTTPBasicAuth(WP_USER, WP_PASS)

TODAY = date.today().strftime("%Y%m%d")


def _parse_date(raw: str) -> str:
    """YYYYMMDD 또는 YYYY-MM-DD → YYYYMMDD"""
    if not raw:
        return ""
    return raw.replace("-", "").replace(".", "").strip()


def _fetch_page(page: int) -> list:
    resp = requests.get(
        f"{WP_URL}/wp-json/wp/v2/policy",
        params={
            "status":   "publish",
            "per_page": 100,
            "page":     page,
            "context":  "edit",
            "_fields":  "id,title,meta",
        },
        auth=AUTH,
        timeout=20,
    )
    if resp.status_code == 400:
        return []
    resp.raise_for_status()
    return resp.json()


def _set_draft(post_id: int, title: str) -> bool:
    resp = requests.post(
        f"{WP_URL}/wp-json/wp/v2/policy/{post_id}",
        json={"status": "draft"},
        auth=AUTH,
        timeout=15,
    )
    ok = resp.status_code in (200, 201)
    if ok:
        print(f"  [비공개] {post_id}: {title[:50]}")
    else:
        print(f"  [실패] {post_id}: {resp.status_code}", file=sys.stderr)
    return ok


def run():
    print(f"만료 포스트 비공개 처리 시작 (기준일: {TODAY})")
    expired = success = 0
    page = 1

    while True:
        posts = _fetch_page(page)
        if not posts:
            break

        for p in posts:
            end_date = _parse_date(p.get("meta", {}).get("application_end_date", ""))
            if not end_date:
                continue
            if end_date < TODAY:
                expired += 1
                title = p.get("title", {}).get("raw", "")
                if _set_draft(p["id"], title):
                    success += 1
                time.sleep(0.5)

        page += 1

    print(f"완료 — 만료 감지: {expired}건, 비공개 처리: {success}건")


if __name__ == "__main__":
    run()