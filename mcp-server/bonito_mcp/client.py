"""HTTP client wrapper for the Bonito REST API."""

from __future__ import annotations

import os
from typing import Any

import httpx


class BonitoClient:
    """Async HTTP client for Bonito API calls."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        self.base_url = (base_url or os.environ.get("BONITO_API_URL", "https://api.getbonito.com")).rstrip("/")
        self.api_key = api_key or os.environ.get("BONITO_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "BONITO_API_KEY is required. Set it as an environment variable or pass it directly."
            )
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(30.0),
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ── Generic request helpers ──────────────────────────────────────

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        client = await self._get_client()
        resp = await client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    async def post(self, path: str, json: dict[str, Any] | None = None) -> Any:
        client = await self._get_client()
        resp = await client.post(path, json=json)
        resp.raise_for_status()
        return resp.json()

    async def put(self, path: str, json: dict[str, Any] | None = None) -> Any:
        client = await self._get_client()
        resp = await client.put(path, json=json)
        resp.raise_for_status()
        return resp.json()

    async def delete(self, path: str) -> Any:
        client = await self._get_client()
        resp = await client.delete(path)
        resp.raise_for_status()
        return resp.json()

    # ── Provider Management ──────────────────────────────────────────

    async def list_providers(self) -> Any:
        return await self.get("/api/providers")

    async def connect_provider(self, provider_type: str, credentials: dict[str, Any]) -> Any:
        return await self.post("/api/providers/connect", json={
            "provider_type": provider_type,
            "credentials": credentials,
        })

    async def verify_provider(self, provider_id: str) -> Any:
        return await self.post(f"/api/providers/{provider_id}/verify")

    # ── Model Management ─────────────────────────────────────────────

    async def list_models(
        self,
        provider: str | None = None,
        capability: str | None = None,
        active: bool | None = None,
    ) -> Any:
        params: dict[str, Any] = {}
        if provider:
            params["provider"] = provider
        if capability:
            params["capability"] = capability
        if active is not None:
            params["active"] = str(active).lower()
        return await self.get("/api/models", params=params or None)

    async def sync_models(self) -> Any:
        return await self.post("/api/models/sync")

    async def activate_model(self, model_id: str) -> Any:
        return await self.post(f"/api/models/{model_id}/activate")

    # ── Gateway ──────────────────────────────────────────────────────

    async def chat_completion(self, model: str, messages: list[dict[str, str]], **kwargs: Any) -> Any:
        payload: dict[str, Any] = {"model": model, "messages": messages, **kwargs}
        return await self.post("/v1/chat/completions", json=payload)

    async def list_gateway_keys(self) -> Any:
        return await self.get("/api/gateway/keys")

    async def create_gateway_key(self, name: str | None = None) -> Any:
        payload: dict[str, Any] = {}
        if name:
            payload["name"] = name
        return await self.post("/api/gateway/keys", json=payload)

    async def gateway_usage(self, period: str | None = None) -> Any:
        params: dict[str, Any] = {}
        if period:
            params["period"] = period
        return await self.get("/api/gateway/usage", params=params or None)

    # ── Agent Management ─────────────────────────────────────────────

    async def list_agents(self, project_id: str) -> Any:
        return await self.get(f"/api/projects/{project_id}/agents")

    async def create_agent(self, project_id: str, agent_config: dict[str, Any]) -> Any:
        return await self.post(f"/api/projects/{project_id}/agents", json=agent_config)

    async def execute_agent(self, agent_id: str, message: str) -> Any:
        return await self.post(f"/api/agents/{agent_id}/execute", json={"message": message})

    async def get_agent(self, agent_id: str) -> Any:
        return await self.get(f"/api/agents/{agent_id}")

    # ── Knowledge Bases ──────────────────────────────────────────────

    async def list_knowledge_bases(self) -> Any:
        return await self.get("/api/knowledge-bases")

    async def create_knowledge_base(self, name: str, description: str | None = None) -> Any:
        payload: dict[str, Any] = {"name": name}
        if description:
            payload["description"] = description
        return await self.post("/api/knowledge-bases", json=payload)

    # ── Cost & Observability ─────────────────────────────────────────

    async def get_costs(self, provider_id: str, period: str | None = None) -> Any:
        params: dict[str, Any] = {}
        if period:
            params["period"] = period
        return await self.get(f"/api/providers/{provider_id}/costs", params=params or None)

    async def get_gateway_logs(
        self,
        limit: int | None = None,
        offset: int | None = None,
        model: str | None = None,
    ) -> Any:
        params: dict[str, Any] = {}
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if model:
            params["model"] = model
        return await self.get("/api/gateway/logs", params=params or None)
