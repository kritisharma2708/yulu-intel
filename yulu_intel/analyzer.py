from typing import List

from openai import OpenAI

from yulu_intel.config import settings
from yulu_intel.models import CompetitiveAnalysis, NewsDigestItem, NewsExtractionResponse
from yulu_intel.prompts import (
    SYSTEM_PROMPT,
    USER_PROMPT_TEMPLATE,
    NEWS_SYSTEM_PROMPT,
    NEWS_USER_PROMPT_TEMPLATE,
)

MAX_SEARCH_DATA_CHARS = 60_000

client = OpenAI(api_key=settings.OPENAI_API_KEY)


def analyze_product(product_name: str, search_data: str) -> CompetitiveAnalysis:
    if len(search_data) > MAX_SEARCH_DATA_CHARS:
        search_data = search_data[:MAX_SEARCH_DATA_CHARS]

    user_prompt = USER_PROMPT_TEMPLATE.format(
        product_name=product_name,
        search_data=search_data,
    )

    completion = client.beta.chat.completions.parse(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format=CompetitiveAnalysis,
    )

    return completion.choices[0].message.parsed


def extract_news(competitor_name: str, search_data: str) -> List[NewsDigestItem]:
    user_prompt = NEWS_USER_PROMPT_TEMPLATE.format(
        competitor_name=competitor_name,
        search_data=search_data,
    )

    completion = client.beta.chat.completions.parse(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": NEWS_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        response_format=NewsExtractionResponse,
    )

    return completion.choices[0].message.parsed.items
