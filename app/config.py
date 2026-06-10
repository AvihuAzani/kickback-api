from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # SQLite by default; set DATABASE_URL to postgresql://... in production
    database_url: str = "sqlite:///./kickback.db"
    secret_key: str = "dev-secret-change-in-production"
    access_token_expire_minutes: int = 10080  # 7 days
    gemini_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
