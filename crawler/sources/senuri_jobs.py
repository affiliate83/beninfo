import os
import time
import requests
import xml.etree.ElementTree as ET
from crawler.utils.logger import get_logger
from crawler.utils.enricher import enrich_job

logger = get_logger("senuri_jobs")

API_KEY  = os.getenv("DATA_GO_KR_API_KEY")
ENDPOINT = os.getenv("SENURI_API_ENDPOINT", "https://apis.data.go.kr/B552474/SenuriService")

EMPL_TYPE = {
    "CM0101": "정규직", "CM0102": "계약직", "CM0103": "시간제",
    "CM0104": "일용직", "CM0105": "기간제", "CM0106": "파견직",
    "CM0107": "용역직", "CM0108": "특수고용", "CM0109": "프리랜서",
    "CM0110": "기타",
}


def _text(el, tag, default=""):
    if el is None:
        return default
    node = el.find(tag)
    return node.text.strip() if node is not None and node.text else default


def _fmt_date(d):
    return f"{d[:4]}-{d[4:6]}-{d[6:]}" if d and len(d) == 8 and d.isdigit() else d


def _get_list(page=1, size=100):
    try:
        res = requests.get(
            f"{ENDPOINT}/getJobList",
            params={"serviceKey": API_KEY, "numOfRows": size, "pageNo": page},
            timeout=15,
        )
        res.raise_for_status()
        root = ET.fromstring(res.content)
        items = root.findall(".//item")
        total_node = root.find(".//totalCount")
        total = int(total_node.text) if total_node is not None and total_node.text else 0
        return items, total
    except Exception as e:
        logger.error("목록 조회 실패 (page=%d): %s", page, e)
        return [], 0


def _get_detail(job_id):
    try:
        res = requests.get(
            f"{ENDPOINT}/getJobInfo",
            params={"serviceKey": API_KEY, "id": job_id},
            timeout=15,
        )
        res.raise_for_status()
        root = ET.fromstring(res.content)
        return root.find(".//item")
    except Exception as e:
        logger.error("상세 조회 실패 (id=%s): %s", job_id, e)
        return None


def _map_category(age_str: str) -> str:
    """나이 요건으로 카테고리 분류 (없으면 고용, 39 이하 → 청년, 50 이상 → 복지)"""
    if not age_str:
        return "고용"
    try:
        age = int("".join(filter(str.isdigit, age_str)))
        if age <= 39:
            return "청년"
        if age >= 50:
            return "복지"
    except ValueError:
        pass
    return "고용"


def _build_content(item, detail) -> str:
    company  = _text(detail, "plbizNm") or _text(item, "oranNm")
    address  = _text(detail, "plDetAddr")
    emp_type = EMPL_TYPE.get(_text(item, "emplymShpNm"), _text(item, "emplymShpNm"))
    start    = _fmt_date(_text(item, "frDd"))
    end      = _fmt_date(_text(item, "toDd"))
    age      = _text(detail, "age")
    count    = _text(detail, "clltPrnnum")
    clerk    = _text(detail, "clerk")
    phone    = _text(detail, "clerkContt")
    homepage = _text(detail, "homepage")
    etc      = _text(detail, "etcItm")

    rows = [
        ("회사명",    company),
        ("근무지",    address),
        ("고용형태",  emp_type),
        ("모집인원",  f"{count}명" if count else ""),
        ("지원연령",  f"{age}세 이상" if age else ""),
        ("모집기간",  f"{start} ~ {end}" if start or end else ""),
        ("담당자",    clerk),
        ("연락처",    phone),
        ("홈페이지",  f'<a href="{homepage}" target="_blank" rel="noopener">{homepage}</a>' if homepage else ""),
        ("기타사항",  etc),
    ]
    table_rows = "\n".join(
        f"  <tr><th>{k}</th><td>{v}</td></tr>" for k, v in rows if v
    )
    return (
        '<div class="job-detail">\n'
        '<h3>채용 정보</h3>\n'
        f'<table class="job-table">\n{table_rows}\n</table>\n'
        "</div>"
    )


def fetch_all(max_pages: int = 10, delay: float = 2.0) -> list[dict]:
    logger.info("시니어/청년 구인정보 수집 시작 (최대 %d페이지)", max_pages)
    results = []

    for page in range(1, max_pages + 1):
        items, total = _get_list(page=page)
        if not items:
            logger.info("페이지 %d — 데이터 없음, 종료", page)
            break

        logger.info("페이지 %d / (전체 %d건) — %d건 처리 중", page, total, len(items))

        for item in items:
            job_id = _text(item, "jobId")
            if not job_id:
                continue

            time.sleep(delay)
            detail   = _get_detail(job_id)
            age_str  = _text(detail, "age") if detail is not None else ""
            category = _map_category(age_str)

            company  = _text(item, "oranNm")
            title_raw = _text(item, "recrtTitle") or company
            # 노인일자리 공고는 제목에 표시, 청년/일반은 그대로
            title = f"[시니어 일자리] {title_raw}" if category == "복지" else title_raw

            end_date_raw = _text(item, "toDd")  # YYYYMMDD

            emp_type = EMPL_TYPE.get(_text(item, "emplymShpNm"), _text(item, "emplymShpNm"))
            address  = _text(detail, "plDetAddr") if detail is not None else ""
            excerpt  = " | ".join(p for p in [company, emp_type, address] if p)

            job_data = {
                "source_id":            f"senuri_{job_id}",
                "source_type":          "senuri_jobs",
                "title":                title,
                "agency_name":          company,
                "benefit_summary":      excerpt,
                "target_audience":      f"{age_str}세 이상" if age_str else "",
                "summary":              excerpt,
                "contact":              _text(detail, "clerkContt") if detail is not None else "",
                "official_link":        _text(detail, "homepage") if detail is not None else "",
                "support_scale":        emp_type,
                "policy_category":      category,
                "application_end_date": end_date_raw,
            }
            base_content = _build_content(item, detail)
            enriched     = enrich_job(job_data)
            job_data["content_override"] = base_content + ("\n" + enriched if enriched else "")
            results.append(job_data)

        if len(items) < 100:
            break
        time.sleep(3)

    logger.info("수집 완료: 총 %d건 (청년: %d, 고용: %d, 복지: %d)",
        len(results),
        sum(1 for r in results if r["policy_category"] == "청년"),
        sum(1 for r in results if r["policy_category"] == "고용"),
        sum(1 for r in results if r["policy_category"] == "복지"),
    )
    return results