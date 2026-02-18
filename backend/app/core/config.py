import os
from typing import Optional
import asyncio
from pydantic_settings import BaseSettings
from app.core.vault import vault_client


class Settings(BaseSettings):
    # Environment-based settings (OK to have defaults)
    database_url: str = "postgresql+asyncpg://bonito:bonito@localhost:5432/bonito"
    
    def get_async_database_url(self) -> str:
        """Convert standard postgresql:// URL to asyncpg format."""
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000,http://localhost:3001,https://getbonito.com"
    
    # Production mode flag
    production_mode: bool = False
    
    # These MUST come from Vault in production (no defaults)
    # Fallback chain: Vault → environment variables → error (prod) / dev defaults (dev)
    secret_key: Optional[str] = None
    encryption_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    notion_api_key: Optional[str] = None
    notion_page_id: Optional[str] = None
    notion_changelog_id: Optional[str] = None
    
    # Platform admin emails (comma-separated)
    admin_emails: str = ""

    # Database connection pool settings
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30

    # Redis connection pool
    redis_max_connections: int = 20

    # Platform admin emails (comma-separated, checked for /api/admin/* access)
    admin_emails: str = ""

    class Config:
        env_file = ".env"

    async def load_secrets_from_vault(self):
        """
        Load secrets with fallback chain: Vault → env vars → error (prod) / defaults (dev).
        
        In production, if Vault is unavailable, falls back to environment variables.
        If neither source provides required secrets, raises an error.
        """
        vault_ok = False
        # Use retries in production (Vault may be starting up alongside us)
        _retries = 5 if self.production_mode else 0
        try:
            # Try Vault first (with retries to survive simultaneous deploys)
            app_secrets = await vault_client.get_secrets("app", retries=_retries)
            api_secrets = await vault_client.get_secrets("api", retries=_retries)
            notion_secrets = await vault_client.get_secrets("notion", retries=_retries)
            
            self.secret_key = app_secrets.get("secret_key") or self.secret_key
            self.encryption_key = app_secrets.get("encryption_key") or self.encryption_key
            self.groq_api_key = api_secrets.get("groq_api_key") or self.groq_api_key
            self.notion_api_key = notion_secrets.get("api_key") or self.notion_api_key
            self.notion_page_id = notion_secrets.get("page_id") or self.notion_page_id
            self.notion_changelog_id = notion_secrets.get("changelog_id") or self.notion_changelog_id
            vault_ok = True
                    
        except Exception as e:
            print(f"Warning: Vault unavailable ({e}), falling back to environment variables")

        # Fallback to environment variables for anything still missing
        self.secret_key = self.secret_key or os.getenv("SECRET_KEY")
        self.encryption_key = self.encryption_key or os.getenv("ENCRYPTION_KEY")
        self.groq_api_key = self.groq_api_key or os.getenv("GROQ_API_KEY")
        self.notion_api_key = self.notion_api_key or os.getenv("NOTION_API_KEY")
        self.notion_page_id = self.notion_page_id or os.getenv("NOTION_PAGE_ID")
        self.notion_changelog_id = self.notion_changelog_id or os.getenv("NOTION_CHANGELOG_ID")

        if self.production_mode:
            # In production, required secrets must exist from either source
            required_secrets = {
                "secret_key": self.secret_key,
                "encryption_key": self.encryption_key,
            }
            missing = [k for k, v in required_secrets.items() if not v]
            if missing:
                raise RuntimeError(
                    f"Missing required secrets (checked Vault {'✓' if vault_ok else '✗'} and env vars): {missing}"
                )
        else:
            # Dev mode: use hardcoded defaults as last resort
            self.secret_key = self.secret_key or "dev-secret-change-in-production"
            self.encryption_key = self.encryption_key or "dev-encryption-key-change-in-production"


# Create settings instance
settings = Settings()

# Set production mode based on environment
settings.production_mode = os.getenv("ENVIRONMENT", "development").lower() == "production"