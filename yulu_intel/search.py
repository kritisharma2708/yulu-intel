import asyncio
import logging
from datetime import datetime, timedelta
from functools import partial
from typing import Dict, List, Set, Tuple

from exa_py import Exa

from yulu_intel.config import settings

logger = logging.getLogger(__name__)

_exa = None

# Exclude social media and non-news domains from results
EXCLUDED_DOMAINS = [
    "linkedin.com",
    "facebook.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "youtube.com",
    "reddit.com",
    "pinterest.com",
    "quora.com",
    "medium.com",
    "wikipedia.org",
]


def _get_exa() -> Exa:
    global _exa
    if _exa is None:
        _exa = Exa(settings.EXA_API_KEY)
    return _exa


INITIAL_QUERIES = [
    "{product} competitors alternatives India micromobility",
    "{product} vs comparison pricing electric scooter bike sharing",
    "{product} market share reviews pros cons India urban mobility",
]

DEEP_QUERIES = [
    "{product} competitor funding raised 2024 2025 India",
    "{product} competitor growth revenue users micromobility India",
    "{product} competitor new features launches 2025 electric mobility",
    "{product} alternatives what's better features bike sharing scooter",
    "{product} alternatives customer complaints problems India",
    "{product} competitor reviews what users love hate",
    "{product} competitor partnerships acquisitions 2025 India",
    "{product} market gaps unmet needs missing features micromobility",
    "{product} industry trends predictions 2025 India EV last mile",
]


def _run_search(
    query: str,
    max_results: int,
    category: str = None,
    start_published_date: str = None,
) -> List[Dict]:
    try:
        exa = _get_exa()
        kwargs = {
            "query": query,
            "type": "auto",
            "num_results": max_results,
            "contents": {"text": {"max_characters": 5000}},
        }
        if category:
            kwargs["category"] = category
            kwargs["exclude_domains"] = EXCLUDED_DOMAINS
        if start_published_date:
            kwargs["start_published_date"] = start_published_date
        response = exa.search(**kwargs)
        results = []
        for r in response.results:
            results.append({
                "title": r.title or "",
                "href": r.url or "",
                "body": r.text or "",
                "published_date": r.published_date or "",
            })
        return results
    except Exception as e:
        logger.warning("Search failed for '%s': %s", query[:60], e)
        return []


def _format_results(results: List[Dict]) -> str:
    text_parts: List[str] = []
    for item in results:
        title = item.get("title", "")
        body = item.get("body", "")
        href = item.get("href", "")
        published = item.get("published_date", "")
        header = f"Title: {title}\nURL: {href}"
        if published:
            header += f"\nPublished: {published}"
        header += f"\nContent: {body}\n"
        text_parts.append(header)
    return "\n---\n".join(text_parts) if text_parts else ""


def _thirty_days_ago() -> str:
    return (datetime.utcnow() - timedelta(days=30)).strftime("%Y-%m-%dT00:00:00.000Z")


async def _run_queries(
    product_name: str,
    templates: List[str],
    seen_urls: Set[str],
    category: str = None,
    start_published_date: str = None,
) -> Tuple[str, Set[str]]:
    loop = asyncio.get_event_loop()
    all_results: List[Dict] = []

    for template in templates:
        query = template.format(product=product_name)
        try:
            result = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    partial(
                        _run_search,
                        query,
                        settings.max_search_results,
                        category,
                        start_published_date,
                    ),
                ),
                timeout=30,
            )
        except asyncio.TimeoutError:
            logger.warning("Timeout for query: %s", query[:60])
            result = []

        for item in result:
            url = item.get("href", "")
            if url not in seen_urls:
                seen_urls.add(url)
                all_results.append(item)

    return _format_results(all_results), seen_urls


async def search_product_initial(product_name: str) -> Tuple[str, Set[str]]:
    seen_urls: Set[str] = set()
    cutoff = _thirty_days_ago()
    text, seen_urls = await _run_queries(
        product_name, INITIAL_QUERIES, seen_urls, start_published_date=cutoff
    )
    return text, seen_urls


async def search_product_deep(
    product_name: str, seen_urls: Set[str]
) -> str:
    cutoff = _thirty_days_ago()
    text, _ = await _run_queries(
        product_name, DEEP_QUERIES, seen_urls, start_published_date=cutoff
    )
    return text


NEWS_QUERIES = [
    "{competitor} electric scooter bike rental gig worker India",
    "{competitor} funding launch partnership expansion India",
]


async def search_competitor_news(competitor_names: List[str]) -> Dict[str, str]:
    """Run news-specific queries for each competitor using Exa news category with date filter."""
    loop = asyncio.get_event_loop()
    results_by_competitor: Dict[str, str] = {}

    # Only fetch news from the last 30 days
    cutoff = _thirty_days_ago()

    for name in competitor_names:
        all_items: List[Dict] = []

        for template in NEWS_QUERIES:
            query = template.format(competitor=name)
            try:
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        partial(
                            _run_search,
                            query,
                            settings.max_search_results,
                            "news",
                            cutoff,
                        ),
                    ),
                    timeout=30,
                )
            except asyncio.TimeoutError:
                logger.warning("Timeout for news query: %s", query[:60])
                result = []

            all_items.extend(result)

        # Deduplicate by URL
        seen = set()
        unique = []
        for item in all_items:
            url = item.get("href", "")
            if url not in seen:
                seen.add(url)
                unique.append(item)

        text = _format_results(unique)
        if text:
            results_by_competitor[name] = text

    return results_by_competitor
