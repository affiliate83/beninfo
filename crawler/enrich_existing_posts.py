"""
기존 발행된 policy 포스트에 AI 풍부화 콘텐츠를 소급 적용한다.
하루 DAILY_LIMIT건씩 실행. faq-item이 이미 있으면 스킵.
"""
import sys, os, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import requests
from requests.auth import HTTPBasicAuth
from crawler.utils.enricher import enrich_policy
from crawler.utils.logger import get_logger

logger   = get_logger("enrich_existing")
WP_URL   = os.getenv("WP_URL", "").rstrip("/")
WP_USER  = os.getenv("WP_USERNAME", "")
WP_PASS  = os.getenv("WP_APP_PASSWORD", "")
AUTH     = HTTPBasicAuth(WP_USER, WP_PASS)

DAILY_LIMIT = 50   # 하루 처리 건수 (Claude API 비용 조절)
DELAY       = 3.0  # 글당 대기 시간(초)


def _get_posts(page: int, per_page: int = 20):
    resp = requests.get(
        f"{WP_URL}/wp-json/wp/v2/policy",
        params={"page": page, "per_page": per_page, "context": "edit",
                "_fields": "id,title,content,meta,excerpt"},
        auth=AUTH, timeout=15,
    )
    if resp.status_code == 400:
        return []
    resp.raise_for_status()
    return resp.json()


def _update_post(post_id: int, new_content: str):
    resp = requests.post(
        f"{WP_URL}/wp-json/wp/v2/policy/{post_id}",
        json={"content": new_content},
        auth=AUTH, timeout=15,
    )
    return resp.status_code in (200, 201)


def run():
    logger.info("기존 포스트 AI 풍부화 시작 (최대 %d건)", DAILY_LIMIT)
    processed = success = skip = 0
    page = 1

    while processed < DAILY_LIMIT:
        posts = _get_posts(page)
        if not posts:
            logger.info("더 이상 포스트 없음 (page=%d)", page)
            break

        for p in posts:
            if processed >= DAILY_LIMIT:
                break

            post_id = p["id"]
            raw     = p.get("content", {}).get("raw", "")
            title   = p.get("title", {}).get("raw", "")

            # 이미 풍부화된 글 스킵
            if "faq-item" in raw:
                skip += 1
                continue

            meta = p.get("meta", {})
            data = {
                "title":           title,
                "summary":         meta.get("benefit_summary", ""),
                "benefit_summary": meta.get("benefit_summary", ""),
                "target_audience": meta.get("target_audience", ""),
                "agency_name":     meta.get("agency_name", ""),
                "select_criteria": "",
            }

            enriched = enrich_policy(data)
            if not enriched:
                logger.warning("  [%d] AI 실패, 스킵", post_id)
                skip += 1
                processed += 1
                time.sleep(DELAY)
                continue

            new_content = raw + "\n" + enriched
            if _update_post(post_id, new_content):
                logger.info("  [%d] 풍부화 완료: %s", post_id, title[:40])
                success += 1
            else:
                logger.warning("  [%d] WP 업데이트 실패", post_id)

            processed += 1
            time.sleep(DELAY)

        page += 1

    logger.info("완료 — 성공: %d, 스킵: %d, 처리: %d", success, skip, processed)


if __name__ == "__main__":
    run()