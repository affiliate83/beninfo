import os
import requests
from requests.auth import HTTPBasicAuth
from crawler.utils.logger import get_logger

logger = get_logger("wordpress")

WP_URL = os.getenv("WP_URL", "").rstrip("/")
WP_USERNAME = os.getenv("WP_USERNAME", "")
WP_APP_PASSWORD = os.getenv("WP_APP_PASSWORD", "")


def _auth():
    return HTTPBasicAuth(WP_USERNAME, WP_APP_PASSWORD)


def _get_or_create_term(taxonomy: str, name: str) -> int | None:
    if not name:
        return None
    resp = requests.get(
        f"{WP_URL}/wp-json/wp/v2/{taxonomy}",
        params={"search": name},
        auth=_auth(),
        timeout=10,
    )
    results = resp.json()
    if isinstance(results, list) and results:
        for item in results:
            if item.get("name") == name:
                return item["id"]

    resp = requests.post(
        f"{WP_URL}/wp-json/wp/v2/{taxonomy}",
        json={"name": name},
        auth=_auth(),
        timeout=10,
    )
    if resp.status_code in (200, 201):
        return resp.json().get("id")
    logger.warning("텀 생성 실패 (%s / %s): %s", taxonomy, name, resp.text)
    return None


def post(item: dict) -> int | None:
    category_id = _get_or_create_term("policy_category", item.get("policy_category"))
    region_id = _get_or_create_term("policy_region", item.get("policy_region"))

    taxonomy_ids = {}
    if category_id:
        taxonomy_ids["policy_category"] = [category_id]
    if region_id:
        taxonomy_ids["policy_region"] = [region_id]

    content = item.get("content_override") or _build_content(item)

    payload = {
        "title": item.get("title", ""),
        "content": content,
        "excerpt": item.get("benefit_summary", "")[:200],
        "status": "publish",
        "type": "policy",
        **taxonomy_ids,
        "meta": {
            "agency_name": item.get("agency_name", ""),
            "target_audience": item.get("target_audience", ""),
            "benefit_summary": item.get("benefit_summary", ""),
            "official_link": item.get("official_link", ""),
            "support_scale": item.get("support_scale", ""),
            "data_source": item.get("official_link", ""),
            "application_end_date": item.get("application_end_date", ""),
            "is_expired": False,
        },
    }

    resp = requests.post(
        f"{WP_URL}/wp-json/wp/v2/policy",
        json=payload,
        auth=_auth(),
        timeout=15,
    )

    if resp.status_code in (200, 201):
        wp_id = resp.json().get("id")
        logger.info("포스팅 성공: [%d] %s", wp_id, item.get("title"))
        return wp_id

    logger.error("포스팅 실패: %s / %s", item.get("title"), resp.text[:200])
    return None


def _build_content(item: dict) -> str:
    def nl2p(text: str) -> str:
        if not text:
            return ""
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        return "".join(f"<p>{l}</p>" for l in lines)

    parts = []

    if item.get("summary"):
        parts.append(f'<div class="policy-summary"><p>{item["summary"]}</p></div>')

    if item.get("target_audience"):
        parts.append(f"<h3>지원 대상</h3>{nl2p(item['target_audience'])}")

    if item.get("benefit_summary"):
        parts.append(f"<h3>지원 내용</h3>{nl2p(item['benefit_summary'])}")

    if item.get("select_criteria"):
        parts.append(f"<h3>선정 기준</h3>{nl2p(item['select_criteria'])}")

    # AI 풍부화 콘텐츠 (있을 때만 추가)
    if item.get("ai_enriched"):
        parts.append(item["ai_enriched"])

    if item.get("agency_name"):
        parts.append(f"<h3>담당 기관</h3><p>{item['agency_name']}</p>")

    if item.get("contact"):
        parts.append(f"<h3>문의처</h3><p>{item['contact']}</p>")

    if item.get("official_link"):
        parts.append(
            f'<div class="policy-cta">'
            f'<a href="{item["official_link"]}" target="_blank" rel="noopener">'
            f'공식 신청 페이지 바로가기 →</a></div>'
        )
    return "\n".join(parts)