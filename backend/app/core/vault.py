"""
HashiCorp Vault client for secure secrets management.

Local dev: Vault runs in dev mode via Docker Compose.
Production: Vault runs in HA mode with proper auth (AppRole, Kubernetes, etc.)

Usage:
    from app.core.vault import vault_client
    
    # Get a secret
    db_url = await vault_client.get_secret("database", "url")
    
    # Get all secrets at a path
    db_secrets = await vault_client.get_secrets("database")
"""

import os
import httpx
from functools import lru_cache
from typing import Optional


class VaultClient:
    def __init__(
        self,
        addr: str = None,
        token: str = None,
        mount: str = None,
    ):
        self.addr = addr or os.getenv("VAULT_ADDR", "http://vault:8200")
        self.token = token or os.getenv("VAULT_TOKEN", "bonito-dev-token")
        self.mount = mount or os.getenv("VAULT_MOUNT", "secret")
        self._cache: dict = {}

    async def get_secrets(self, path: str) -> dict:
        """Get all key-value pairs at a secret path."""
        if path in self._cache:
            return self._cache[path]

        url = f"{self.addr}/v1/{self.mount}/data/{path}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                headers={"X-Vault-Token": self.token},
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()["data"]["data"]
                self._cache[path] = data
                return data
            elif resp.status_code == 404:
                return {}
            else:
                raise Exception(
                    f"Vault error ({resp.status_code}): {resp.text}"
                )

    async def get_secret(self, path: str, key: str, default: str = None) -> Optional[str]:
        """Get a single secret value."""
        secrets = await self.get_secrets(path)
        return secrets.get(key, default)

    async def put_secrets(self, path: str, data: dict) -> bool:
        """Write secrets to a path."""
        url = f"{self.addr}/v1/{self.mount}/data/{path}"
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                headers={"X-Vault-Token": self.token},
                json={"data": data},
                timeout=5.0,
            )
            if resp.status_code in (200, 204):
                self._cache.pop(path, None)  # Invalidate cache
                return True
            raise Exception(f"Vault write error ({resp.status_code}): {resp.text}")

    def clear_cache(self):
        """Clear the in-memory cache."""
        self._cache.clear()

    async def health_check(self) -> dict:
        """Check Vault health status."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self.addr}/v1/sys/health",
                    timeout=3.0,
                )
                return {"status": "healthy", "code": resp.status_code}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}


# Singleton instance
vault_client = VaultClient()
