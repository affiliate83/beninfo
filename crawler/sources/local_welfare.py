import time
import os
import requests
from lxml import etree
from crawler.utils.logger import get_logger

logger = get_logger("local_welfare")

BASE_URL = "https://apis.data.go.kr/B554287/LocalGovernmentWelfareInformations"
API_KEY = os.getenv("DATA_GO_KR_API_KEY")


def _get(endpoint: str, params: dict) -> etree._Element:
    params["serviceKey"] = API_KEY
    resp = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=15)
    resp.raise_for_status()
    return etree.fromstring(resp.content)


def _text(el, tag: str) -> str:
    node = el.find(tag)
    return node.text.strip() if node is not None and node.text else ""


def _normalize_date(raw: str) -> str:
    if not raw:
        return ""
    cleaned = raw.replace("-", "").replace("/", "").replace(".", "").strip()
    return cleaned if len(cleaned) == 8 and cleaned.isdigit() else ""


def fetch_list(page: int = 1, num_of_rows: int = 100) -> list[dict]:
    root = _get("LocalGovernmentWelfarelist", {"srchKeyCode": "001", "pageNo": page, "numOfRows": num_of_rows})

    result_code = _text(root, ".//resultCode")
    if result_code not in ("0", "00", "0000"):
        logger.error("API 오류 [%s]: %s", result_code, _text(root, ".//resultMessage"))
        return []

    items = []
    for item in root.findall(".//servList"):
        region   = _text(item, "ctpvNm") or "전국"
        end_date = _normalize_date(_text(item, "aplyEndDt") or _text(item, "servEndDt"))
        data = {
            "source_id":            f"local_{_text(item, 'servId')}",
            "source_type":          "local_welfare",
            "title":                _text(item, "servNm"),
            "agency_name":          _text(item, "jurOrgNm"),
            "target_audience":      _text(item, "tgtrDtlCd"),
            "benefit_summary":      _text(item, "srvContent"),
            "official_link":        _text(item, "servDtlLink"),
            "policy_region":        region,
            "policy_category":      "복지",
            "application_end_date": end_date,
        }
        items.append(data)
    return items


def fetch_all(delay: float = 2.0) -> list[dict]:
    logger.info("지자체 복지서비스 전체 수집 시작")
    first = _get("LocalGovernmentWelfarelist", {"srchKeyCode": "001", "pageNo": 1, "numOfRows": 1})
    total = int(_text(first, ".//totalCount") or 0)
    num_of_rows = 100
    total_pages = (total + num_of_rows - 1) // num_of_rows
    logger.info("총 %d건 / %d페이지", total, total_pages)

    all_items = []
    for page in range(1, total_pages + 1):
        logger.info("페이지 %d / %d 수집 중...", page, total_pages)
        items = fetch_list(page=page, num_of_rows=num_of_rows)
        all_items.extend(items)
        time.sleep(delay)

    logger.info("지자체 수집 완료: 총 %d건", len(all_items))
    return all_items