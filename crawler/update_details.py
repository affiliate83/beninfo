import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

import requests
from lxml import etree
from crawler.utils.dedup import get_pending_detail, mark_detail_fetched
from crawler.utils.logger import get_logger
from crawler.poster.wordpress import _build_content, _auth

logger = get_logger("update_details")

BASE_URL = "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001"
API_KEY = os.getenv("DATA_GO_KR_API_KEY")
WP_URL = os.getenv("WP_URL", "").rstrip("/")

DAILY_LIMIT = 100
DELAY = 5.0


def _text(el, tag: str) -> str:
    node = el.find(tag)
    return node.text.strip() if node is not None and node.text else ""


def _normalize_date(raw: str) -> str:
    if not raw:
        return ""
    cleaned = raw.replace("-", "").replace("/", "").replace(".", "").strip()
    return cleaned if len(cleaned) == 8 and cleaned.isdigit() else ""


def fetch_detail(serv_id: str) -> dict:
    resp = requests.get(
        f"{BASE_URL}/NationalWelfaredetailedV001",
        params={"callTp": "D", "servId": serv_id, "serviceKey": API_KEY},
        timeout=15,
    )
    if resp.status_code == 429:
        logger.warning("429 Rate Limit — 오늘 한도 초과, 중단합니다")
        return None
    resp.raise_for_status()
    root = etree.fromstring(resp.content)
    return {
        "target_audience": _text(root, "tgtrDtlCn"),
        "benefit_summary": _text(root, "alwServCn"),
        "select_criteria": _text(root, "slctCritCn"),
        "summary": _text(root, "wlfareInfoOutlCn"),
        "contact": _text(root, "rprsCtadr"),
        "agency_name": _text(root, "jurMnofNm"),
        "application_end_date": _normalize_date(_text(root, "aplyEndDt")),
    }


def update_wp_post(wp_post_id: int, item: dict):
    content = _build_content(item)
    excerpt = (item.get("summary") or item.get("benefit_summary", ""))[:200]
    resp = requests.post(
        f"{WP_URL}/wp-json/wp/v2/policy/{wp_post_id}",
        json={
            "content": content,
            "excerpt": excerpt,
            "meta": {
                "target_audience": item.get("target_audience", ""),
                "benefit_summary": item.get("benefit_summary", ""),
                "agency_name": item.get("agency_name", ""),
                "application_end_date": item.get("application_end_date", ""),
            },
        },
        auth=_auth(),
        timeout=15,
    )
    return resp.status_code in (200, 201)


def run():
    pending = get_pending_detail("national_welfare", limit=DAILY_LIMIT)
    total = len(pending)
    logger.info("상세 업데이트 시작 — 오늘 처리할 건수: %d", total)

    success = fail = skipped = 0
    for idx, (source_id, wp_post_id) in enumerate(pending, 1):
        serv_id = source_id.replace("national_", "")
        logger.info("  (%d/%d) %s → WP#%d", idx, total, serv_id, wp_post_id or 0)

        detail = fetch_detail(serv_id)
        if detail is None:
            logger.warning("오늘 API 한도 초과 — 중단 (처리: %d건)", idx - 1)
            break

        if not any(detail.values()):
            logger.warning("  상세 데이터 없음, 스킵")
            mark_detail_fetched(source_id)
            skipped += 1
            time.sleep(DELAY)
            continue

        if wp_post_id and update_wp_post(wp_post_id, detail):
            mark_detail_fetched(source_id)
            success += 1
        else:
            fail += 1

        time.sleep(DELAY)

    logger.info("완료 — 성공: %d, 실패: %d, 스킵: %d", success, fail, skipped)


if __name__ == "__main__":
    run()