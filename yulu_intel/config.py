from pydantic_settings import BaseSettings


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
