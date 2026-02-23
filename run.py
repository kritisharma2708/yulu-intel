import asyncio
import logging
import sys

from yulu_intel.config import settings
from yulu_intel.db import detect_and_store, init_db, is_first_run
from yulu_intel.search import search_product_initial, search_product_deep, search_competitor_news
from yulu_intel.analyzer import analyze_product, extract_news
from yulu_intel.formatter import format_messages
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

    # 6. Format Slack messages
    logger.info("Phase 6: Formatting Slack messages...")
    payloads = format_messages(analysis, new_competitors, returning_competitors, first_run)
    logger.info("  Built %d messages", len(payloads))

    # 7. Send to Slack
    logger.info("Phase 7: Sending to Slack...")
    send_messages(payloads)
    logger.info("=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
