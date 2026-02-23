import asyncio
from functools import partial
from typing import Dict, List, Set, Tuple

from ddgs import DDGS

from yulu_intel.config import settings


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


def _run_search(query: str, max_results: int) -> List[Dict]:
    ddgs = DDGS()
    return list(ddgs.text(query, max_results=max_results))


def _format_results(results: List[Dict]) -> str:
    text_parts: List[str] = []
    for item in results:
        title = item.get("title", "")
        body = item.get("body", "")
        href = item.get("href", "")
        text_parts.append(f"Title: {title}\nURL: {href}\nSnippet: {body}\n")
    return "\n---\n".join(text_parts) if text_parts else ""


async def _run_queries(
    product_name: str,
    templates: List[str],
    seen_urls: Set[str],
) -> Tuple[str, Set[str]]:
    loop = asyncio.get_event_loop()
    all_results: List[Dict] = []

    tasks = [
        loop.run_in_executor(
            None,
            partial(
                _run_search,
                template.format(product=product_name),
                settings.max_search_results,
            ),
        )
        for template in templates
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            continue
        for item in result:
            url = item.get("href", "")
            if url not in seen_urls:
                seen_urls.add(url)
                all_results.append(item)

    return _format_results(all_results), seen_urls


async def search_product_initial(product_name: str) -> Tuple[str, Set[str]]:
    seen_urls: Set[str] = set()
    text, seen_urls = await _run_queries(product_name, INITIAL_QUERIES, seen_urls)
    return text, seen_urls


async def search_product_deep(
    product_name: str, seen_urls: Set[str]
) -> str:
    text, _ = await _run_queries(product_name, DEEP_QUERIES, seen_urls)
    return text


NEWS_QUERIES = [
    "{competitor} news site:techcrunch.com OR site:economictimes.com OR site:inc42.com OR site:entrackr.com after:2026-01-01",
    "{competitor} announcement January 2026 OR February 2026",
]


async def search_competitor_news(competitor_names: List[str]) -> Dict[str, str]:
    """Run news-specific queries for each competitor. Returns {name: search_text}."""
    loop = asyncio.get_event_loop()
    results_by_competitor: Dict[str, str] = {}

    for name in competitor_names:
        tasks = [
            loop.run_in_executor(
                None,
                partial(
                    _run_search,
                    template.format(competitor=name),
                    settings.max_search_results,
                ),
            )
            for template in NEWS_QUERIES
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_items: List[Dict] = []
        for result in results:
            if isinstance(result, Exception):
                continue
            all_items.extend(result)

        text = _format_results(all_items)
        if text:
            results_by_competitor[name] = text

    return results_by_competitor
