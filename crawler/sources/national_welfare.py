import time
import os
import requests
from lxml import etree
from crawler.utils.logger import get_logger
from crawler.utils.enricher import enrich_policy

logger = get_logger("national_welfare")

BASE_URL = "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001"
API_KEY = os.getenv("DATA_GO_KR_API_KEY")


def _get(endpoint: str, params: dict, retries: int = 3) -> etree._Element:
    params["serviceKey"] = API_KEY
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=15)
            if resp.status_code == 429:
                wait = 10 * attempt
                logger.warning("429 Rate Limit — %d초 대기 후 재시도 (%d/%d)", wait, attempt, retries)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return etree.fromstring(resp.content)
        except Exception as e:
            logger.warning("요청 실패 (%d/%d): %s", attempt, retries, e)
            if attempt < retries:
                time.sleep(5 * attempt)
    raise Exception(f"API 호출 {retries}회 실패: {endpoint}")


def _text(el, tag: str) -> str:
    node = el.find(tag)
    return node.text.strip() if node is not None and node.text else ""


def _normalize_date(raw: str) -> str:
    """YYYYMMDD / YYYY-MM-DD / YYYY.MM.DD → YYYYMMDD, 나머지는 빈 문자열"""
    if not raw:
        return ""
    cleaned = raw.replace("-", "").replace("/", "").replace(".", "").strip()
    return cleaned if len(cleaned) == 8 and cleaned.isdigit() else ""


def _fetch_detail(serv_id: str) -> dict:
    try:
        root = _get("NationalWelfaredetailedV001", {"callTp": "D", "servId": serv_id}, retries=1)
        return {
            "target_audience": _text(root, "tgtrDtlCn"),
            "benefit_summary": _text(root, "alwServCn"),
            "select_criteria": _text(root, "slctCritCn"),
            "summary": _text(root, "wlfareInfoOutlCn"),
            "contact": _text(root, "rprsCtadr"),
            "application_end_date": _normalize_date(_text(root, "aplyEndDt")),
        }
    except Exception as e:
        logger.warning("상세 조회 실패 (%s) — 목록 데이터로 대체: %s", serv_id, e)
        return {}


def fetch_list(page: int = 1, num_of_rows: int = 100, detail_delay: float = 5.0) -> list[dict]:
    root = _get(
        "NationalWelfarelistV001",
        {"srchKeyCode": "001", "pageNo": page, "numOfRows": num_of_rows},
    )

    result_code = _text(root, ".//resultCode")
    if result_code not in ("0", "00", "0000"):
        logger.error("API 오류 [%s]: %s", result_code, _text(root, ".//resultMessage"))
        return []

    items = []
    for item in root.findall(".//servList"):
        serv_id  = _text(item, "servId")
        category = _map_category(_text(item, "lifeArray") or _text(item, "intrsThemaArray"))
        data = {
            "source_id":       f"national_{serv_id}",
            "source_type":     "national_welfare",
            "title":           _text(item, "servNm"),
            "agency_name":     _text(item, "jurMnofNm"),
            "target_audience": _text(item, "intrsThemaArray"),
            "benefit_summary": _text(item, "servDgst"),
            "select_criteria": "",
            "summary":         _text(item, "servDgst"),
            "contact":         _text(item, "rprsCtadr"),
            "official_link":   _text(item, "servDtlLink"),
            "support_scale":   _text(item, "srvPvsnNm"),
            "policy_category": category,
        }
        data["ai_enriched"] = enrich_policy(data)
        items.append(data)
    return items


def fetch_all(delay: float = 2.0) -> list[dict]:
    logger.info("중앙부처 복지서비스 전체 수집 시작 (상세 포함)")
    first = _get("NationalWelfarelistV001", {"srchKeyCode": "001", "pageNo": 1, "numOfRows": 1})
    total = int(_text(first, ".//totalCount") or 0)
    num_of_rows = 50
    total_pages = (total + num_of_rows - 1) // num_of_rows
    logger.info("총 %d건 / %d페이지 (페이지당 %d건)", total, total_pages, num_of_rows)

    all_items = []
    for page in range(1, total_pages + 1):
        logger.info("페이지 %d / %d 수집 중...", page, total_pages)
        items = fetch_list(page=page, num_of_rows=num_of_rows)
        all_items.extend(items)
        time.sleep(delay)

    logger.info("중앙부처 수집 완료: 총 %d건", len(all_items))
    return all_items


def _map_category(life_array: str) -> str:
    mapping = {
        "영유아": "복지", "아동": "복지", "청소년": "청년", "청년": "청년",
        "중장년": "복지", "노년": "복지", "장애인": "복지",
        "임신·출산": "복지", "한부모": "복지", "다문화": "복지",
        "서민금융": "복지", "고용": "고용", "취업": "고용",
        "주거": "주거", "창업": "창업", "교육": "교육",
        "보건": "보건의료", "의료": "보건의료",
        "농림": "농림어업", "어업": "농림어업",
        "문화": "문화생활",
    }
    for key, category in mapping.items():
        if key in life_array:
            return category
    return "복지"