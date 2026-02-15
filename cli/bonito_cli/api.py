"""HTTP API client for Bonito backend."""

import httpx
from typing import Dict, Any, Optional, List, Union
from rich.console import Console
import json

from .config import get_api_url, get_api_key, load_credentials, save_credentials

console = Console()


class APIError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class BonitoAPI:
    """Sync Bonito API client."""
    
    def __init__(self):
        self.base_url = get_api_url()
        self._client: Optional[httpx.Client] = None
    
    @property
    def client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(base_url=self.base_url, timeout=30.0, follow_redirects=True)
        return self._client
    
    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json", "User-Agent": "bonito-cli/0.1.0"}
        token = get_api_key()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers
    
    def _request(self, method: str, endpoint: str, data=None, params=None) -> Any:
        url = endpoint if endpoint.startswith("http") else f"/api{endpoint}"
        try:
            resp = self.client.request(method, url, json=data, params=params, headers=self._headers())
        except httpx.RequestError as e:
            raise APIError(f"Connection failed: {e}")
        
        if resp.status_code == 401:
            raise APIError("Authentication failed. Run 'bonito auth login'.", 401)
        if resp.status_code == 204:
            return {"status": "deleted"}
        if resp.status_code >= 400:
            try:
                err = resp.json()
                msg = err.get("detail", err.get("error", {}).get("message", f"HTTP {resp.status_code}"))
            except Exception:
                msg = f"HTTP {resp.status_code}: {resp.text[:200]}"
            raise APIError(str(msg), resp.status_code)
        
        try:
            return resp.json()
        except Exception:
            return {"status": "ok", "text": resp.text}
    
    def get(self, endpoint: str, params=None) -> Any:
        return self._request("GET", endpoint, params=params)
    
    def post(self, endpoint: str, data=None) -> Any:
        return self._request("POST", endpoint, data=data)
    
    def put(self, endpoint: str, data=None) -> Any:
        return self._request("PUT", endpoint, data=data)
    
    def delete(self, endpoint: str) -> Any:
        return self._request("DELETE", endpoint)
    
    def stream_chat(self, url: str, data: dict, headers: dict):
        """Stream a chat completion (SSE)."""
        with httpx.stream("POST", url, json=data, headers=headers, timeout=60.0) as resp:
            if resp.status_code >= 400:
                raise APIError(f"HTTP {resp.status_code}: {resp.read().decode()[:200]}", resp.status_code)
            for line in resp.iter_lines():
                if line.startswith("data: "):
                    chunk = line[6:]
                    if chunk.strip() == "[DONE]":
                        break
                    try:
                        yield json.loads(chunk)
                    except json.JSONDecodeError:
                        continue


# Global instance
api = BonitoAPI()
