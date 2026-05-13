"""Synchronous HTTP API client for the Bonito backend."""

from __future__ import annotations

import json
from typing import Any, Dict, Generator, Optional

import httpx
from rich.console import Console

from . import __version__
from .config import get_api_key, get_api_url, get_refresh_token, save_credentials, load_credentials

console = Console()


class APIError(Exception):
    """Raised when an API request fails."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class BonitoAPI:
    """Synchronous Bonito API client backed by ``httpx.Client``."""

    def __init__(self) -> None:
        self.base_url: str = get_api_url()
        self._client: Optional[httpx.Client] = None
        self._refreshing: bool = False

    # ── internal helpers ────────────────────────────────────────

    @property
    def client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                base_url=self.base_url,
                timeout=30.0,
                follow_redirects=True,
            )
        return self._client

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "User-Agent": f"bonito-cli/{__version__}",
        }
        token = get_api_key()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _try_refresh(self) -> bool:
        """Attempt to refresh the access token using the stored refresh token."""
        refresh_token = get_refresh_token()
        if not refresh_token:
            return False
        self._refreshing = True
        try:
            resp = self.client.request(
                "POST", "/api/auth/refresh",
                json={"refresh_token": refresh_token},
                headers={"Content-Type": "application/json", "User-Agent": f"bonito-cli/{__version__}"},
            )
            if resp.status_code == 200:
                tokens = resp.json()
                creds = load_credentials()
                creds["access_token"] = tokens["access_token"]
                if tokens.get("refresh_token"):
                    creds["refresh_token"] = tokens["refresh_token"]
                save_credentials(creds)
                return True
        except Exception:
            pass
        finally:
            self._refreshing = False
        return False

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Any = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        url = endpoint if endpoint.startswith("http") else f"/api{endpoint}"
        try:
            resp = self.client.request(
                method, url, json=data, params=params, headers=self._headers()
            )
        except httpx.RequestError as exc:
            raise APIError(f"Connection failed: {exc}") from exc

        if resp.status_code == 401 and not self._refreshing:
            if self._try_refresh():
                # Retry the request with the new token
                try:
                    resp = self.client.request(
                        method, url, json=data, params=params, headers=self._headers()
                    )
                except httpx.RequestError as exc:
                    raise APIError(f"Connection failed: {exc}") from exc
            if resp.status_code == 401:
                raise APIError(
                    "Authentication failed — run [cyan]bonito auth login[/cyan].", 401
                )
        if resp.status_code == 204:
            return {"status": "ok"}
        if resp.status_code >= 400:
            try:
                body = resp.json()
                detail = body.get(
                    "detail",
                    body.get("error", {}).get("message", f"HTTP {resp.status_code}"),
                )
            except Exception:
                detail = f"HTTP {resp.status_code}: {resp.text[:200]}"

            # Parse Pydantic 422 validation errors into friendly messages
            if resp.status_code == 422 and isinstance(detail, list):
                parts: list[str] = []
                for err in detail:
                    if isinstance(err, dict):
                        err_type = err.get("type", "")
                        err_msg = err.get("msg", "Validation error")
                        loc = err.get("loc", [])
                        field = str(loc[-1]).replace("_", " ") if loc else "input"
                        if err_type == "uuid_parsing":
                            parts.append(
                                f"Invalid {field} format. "
                                "Expected a UUID (e.g. a1b2c3d4-e5f6-...)"
                            )
                        else:
                            parts.append(f"{err_msg} (field: {field})")
                    else:
                        parts.append(str(err))
                msg = "; ".join(parts) if parts else "Validation error"
            elif isinstance(detail, list):
                msg = "; ".join(str(d) for d in detail)
            else:
                msg = str(detail)

            raise APIError(msg, resp.status_code)

        try:
            return resp.json()
        except Exception:
            return {"status": "ok", "text": resp.text}

    # ── public verbs ────────────────────────────────────────────

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._request("GET", endpoint, params=params)

    def post(self, endpoint: str, data: Any = None) -> Any:
        return self._request("POST", endpoint, data=data)

    def put(self, endpoint: str, data: Any = None) -> Any:
        return self._request("PUT", endpoint, data=data)

    def patch(self, endpoint: str, data: Any = None) -> Any:
        return self._request("PATCH", endpoint, data=data)

    def delete(self, endpoint: str) -> Any:
        return self._request("DELETE", endpoint)

    # ── streaming (SSE) ─────────────────────────────────────────

    def stream_post(
        self,
        url: str,
        data: dict,
        headers: Optional[Dict[str, str]] = None,
    ) -> Generator[dict, None, None]:
        """Stream a POST request that returns SSE ``data:`` lines."""
        hdrs = self._headers()
        if headers:
            hdrs.update(headers)

        full_url = url if url.startswith("http") else f"{self.base_url}{url}"

        with httpx.stream(
            "POST", full_url, json=data, headers=hdrs, timeout=120.0
        ) as resp:
            if resp.status_code >= 400:
                raise APIError(
                    f"HTTP {resp.status_code}: {resp.read().decode()[:200]}",
                    resp.status_code,
                )
            for line in resp.iter_lines():
                if line.startswith("data: "):
                    chunk = line[6:]
                    if chunk.strip() == "[DONE]":
                        break
                    try:
                        yield json.loads(chunk)
                    except json.JSONDecodeError:
                        continue


# ── module-level singleton ──────────────────────────────────────
api = BonitoAPI()
