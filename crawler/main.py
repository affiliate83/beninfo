import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from crawler.sources.national_welfare import fetch_all as fetch_national
from crawler.sources.local_welfare import fetch_all as fetch_local
from crawler.sources.senuri_jobs import fetch_all as fetch_senuri
from crawler.poster.wordpress import post
from crawler.utils.dedup import is_seen, mark_seen
from crawler.utils.enricher import enrich_job, enrich_policy
from crawler.utils.logger import get_logger

logger = get_logger("main")


def _enrich(item: dict) -> None:
    """신규 글에만 AI 풍부화 적용 (중복 체크 이후 호출)."""
    source_type = item.get("source_type", "")
    if source_type == "senuri_jobs":
        enriched = enrich_job(item)
        if enriched:
            base = item.get("content_override", "")
            item["content_override"] = base + "\n" + enriched
    elif source_type in ("national_welfare", "local_welfare"):
        item["ai_enriched"] = enrich_policy(item)


SOURCES = {
    "national": fetch_national,
    "local":    fetch_local,
    "senuri":   fetch_senuri,
}


def run(sources: list[str], dry_run: bool = False, max_pages: int = None):
    for source_name in sources:
        fetch_fn = SOURCES.get(source_name)
        if not fetch_fn:
            logger.warning("알 수 없는 소스: %s", source_name)
            continue

        kwargs = {}
        if max_pages is not None and source_name == "senuri":
            kwargs["max_pages"] = max_pages
        # dry-run 시 enrichment 비활성화
        if dry_run:
            import os
            os.environ["SKIP_ENRICHMENT"] = "1"

        items = fetch_fn(**kwargs)
        new_count = skip_count = fail_count = 0

        for item in items:
            source_id = item.get("source_id", "")

            if is_seen(source_id):
                skip_count += 1
                continue

            if dry_run:
                logger.info("[DRY-RUN] %s", item.get("title"))
                new_count += 1
                continue

            _enrich(item)
            wp_id = post(item)
            if wp_id:
                mark_seen(source_id, item.get("source_type", ""), wp_id)
                new_count += 1
            else:
                fail_count += 1

        logger.info(
            "[%s] 완료 — 신규: %d, 중복 스킵: %d, 실패: %d",
            source_name, new_count, skip_count, fail_count,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BenefitInfo 크롤러")
    parser.add_argument(
        "--source",
        choices=list(SOURCES.keys()) + ["all"],
        default="all",
        help="수집할 소스 (기본값: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="WordPress에 실제 포스팅하지 않고 수집만 테스트",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=None,
        help="수집 페이지 수 제한 (테스트용, senuri만 적용)",
    )
    args = parser.parse_args()

    target_sources = list(SOURCES.keys()) if args.source == "all" else [args.source]
    run(target_sources, dry_run=args.dry_run, max_pages=args.pages)