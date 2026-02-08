from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://bonito:bonito@localhost:5432/bonito"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "dev-secret-change-in-production"
    cors_origins: str = "http://localhost:3000"
    encryption_key: str = "dev-encryption-key-change-in-production"
    groq_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
