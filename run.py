import asyncio
import logging
import os
import sys
from datetime import date

from yulu_intel.config import settings
from yulu_intel.db import detect_and_store, init_db, is_first_run
from yulu_intel.search import search_product_initial, search_product_deep, search_competitor_news
from yulu_intel.analyzer import analyze_product, extract_news
from yulu_intel.formatter import format_summary
from yulu_intel.html_report import generate_html_report
from yulu_intel.slack import send_messages

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    product = settings.PRODUCT_NAME
    logger.info("=== Yulu Competitive Intel Run: %s ===", product)

    # 1. Init DB
    init_db()
    first_run = is_first_run()
    if first_run:
        logger.info("First run detected — all competitors will be marked as new")

    # 2. Search
    logger.info("Phase 1: Initial search...")
    initial_text, seen_urls = await search_product_initial(product)
    logger.info("  Initial search returned %d chars", len(initial_text))

    logger.info("Phase 2: Deep search...")
    deep_text = await search_product_deep(product, seen_urls)
    logger.info("  Deep search returned %d chars", len(deep_text))

    search_data = initial_text
    if deep_text:
        search_data = search_data + "\n---\n" + deep_text

    # 3. Analyze
    logger.info("Phase 3: AI analysis...")
    analysis = await asyncio.to_thread(analyze_product, product, search_data)
    logger.info("  Found %d competitors", len(analysis.competitors))

    # 4. News search + extraction per competitor
    competitor_names = [c.name for c in analysis.competitors]
    logger.info("Phase 4: News search for %d competitors...", len(competitor_names))
    news_data = await search_competitor_news(competitor_names)
    logger.info("  Got news search results for: %s", list(news_data.keys()) or "(none)")

    all_news = []
    for name, search_text in news_data.items():
        items = await asyncio.to_thread(extract_news, name, search_text)
        linked = [item for item in items if item.url]
        all_news.extend(linked)
        logger.info("  %s: %d news items (%d with URLs)", name, len(items), len(linked))

    analysis.news_digest = all_news
    logger.info("  Total news items: %d", len(all_news))

    # 5. Detect new competitors
    logger.info("Phase 5: Competitor tracking...")
    new_competitors, returning_competitors = detect_and_store(analysis)
    logger.info("  New: %s", new_competitors or "(none)")
    logger.info("  Returning: %s", returning_competitors or "(none)")

    # 6. Generate HTML report
    logger.info("Phase 6: Generating HTML report...")
    report_html = generate_html_report(analysis, new_competitors, returning_competitors, first_run)

    # Write to local file
    reports_dir = os.path.join(os.path.dirname(__file__), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    today_str = date.today().isoformat()
    report_path = os.path.join(reports_dir, f"{today_str}.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_html)
    logger.info("  Report saved to %s", report_path)

    # Store in Supabase (update the row we just inserted)
    try:
        from supabase import create_client
        sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        sb.table("analysis_runs").update({
            "report_html": report_html,
        }).eq("run_date", today_str).eq("product_name", product).execute()
        logger.info("  Report HTML stored in Supabase")
    except Exception as exc:
        logger.warning("  Could not store report HTML in Supabase: %s", exc)

    # 7. Build short Slack summary
    logger.info("Phase 7: Formatting Slack summary...")
    report_url = None
    if settings.REPORT_BASE_URL:
        report_url = f"{settings.REPORT_BASE_URL.rstrip('/')}/report/{today_str}"
    payloads = format_summary(analysis, report_url)
    logger.info("  Built %d message(s)", len(payloads))

    # 8. Send to Slack
    logger.info("Phase 8: Sending to Slack...")
    send_messages(payloads)
    logger.info("=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
