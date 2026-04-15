"""
Vercel API client for Helios — fetches deployments and logs.

Reference: https://vercel.com/docs/rest/api
"""

import logging
from typing import Optional, Dict, Any, List

import httpx

logger = logging.getLogger("helios.vercel")

VERCEL_API = "https://api.vercel.com"


class VercelClient:
    """Async Vercel REST API client."""

    def __init__(self, token: str):
        self.token = token
        self._client = httpx.AsyncClient(
            base_url=VERCEL_API,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )

    async def close(self):
        await self._client.aclose()

    async def list_deployments(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch recent deployments for the authenticated user/team."""
        resp = await self._client.get("/v6/deployments", params={"limit": limit})
        resp.raise_for_status()
        data = resp.json()
        return data.get("deployments", [])

    async def get_deployment_events(self, deployment_id: str) -> List[Dict[str, Any]]:
        """
        Fetch build/runtime events for a specific deployment.
        Returns structured log lines.
        """
        resp = await self._client.get(f"/v2/deployments/{deployment_id}/events")
        resp.raise_for_status()
        data = resp.json()
        events = []
        for line in data.get("lines", []):
            events.append({
                "timestamp": line.get("ts"),
                "level": line.get("level", "info"),
                "text": line.get("text", ""),
            })
        return events

    async def retry_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """Retry a failed deployment."""
        resp = await self._client.post(f"/v2/deployments/{deployment_id}/retry")
        resp.raise_for_status()
        return resp.json()

    async def rollback(self, deployment_id: str) -> Dict[str, Any]:
        """Rollback to the previous deployment."""
        deployments = await self.list_deployments(limit=5)
        if len(deployments) < 2:
            raise ValueError("No previous deployment to rollback to")
        
        prev = deployments[1]  # Most recent before current
        resp = await self._client.post(
            f"/v1/deployments/{prev['uid']}/rollback",
            json={"from": deployment_id}
        )
        resp.raise_for_status()
        return resp.json()

    async def get_deployment_logs(self, deployment_id: str) -> Dict[str, Any]:
        """
        Fetch combined deployment logs (build + runtime).
        This is the primary log source for Helios.
        """
        resp = await self._client.get(f"/v2/deployments/{deployment_id}/events")
        if resp.status_code == 404:
            # Fallback for older deployments
            resp = await self._client.get(f"/v6/deployments/{deployment_id}")
        resp.raise_for_status()
        return resp.json()

    async def get_project(self, project_id: str) -> Dict[str, Any]:
        """Get project details."""
        resp = await self._client.get(f"/v2/projects/{project_id}")
        resp.raise_for_status()
        return resp.json()