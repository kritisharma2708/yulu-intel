from pydantic_settings import BaseSettings


FOCUS_PERSONA = {
    "segment": "gig workers and daily bike renters",
    "useCases": [
        "last-mile delivery",
        "food delivery",
        "hyperlocal logistics",
        "daily commute rentals",
        "subscription bike rentals",
    ],
    "keyConcerns": [
        "per-km cost",
        "vehicle availability",
        "battery reliability",
        "earnings impact",
        "subscription plans",
        "rental affordability",
    ],
}


class Settings(BaseSettings):
    OPENAI_API_KEY: str
    openai_model: str = "gpt-4o-mini"
    max_search_results: int = 5
    PRODUCT_NAME: str = "Yulu"
    SLACK_WEBHOOK_URL: str = ""
    SLACK_BOT_TOKEN: str = ""
    SLACK_CHANNEL: str = ""
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    model_config = {"env_file": ".env"}


settings = Settings()
