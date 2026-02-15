"""HTTP API client for Bonito backend."""

import asyncio
import httpx
from typing import Dict, Any, Optional, List, Union
from rich.console import Console
import json
from datetime import datetime, timedelta

from .config import (
    get_api_url, get_api_key, get_refresh_token, 
    save_credentials, load_credentials, is_authenticated
)

console = Console()


class APIError(Exception):
    """API request error."""
    def __init__(self, message: str, status_code: Optional[int] = None, response_data: Optional[Dict] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data


class BonitoAPI:
    """Bonito API client."""
    
    def __init__(self):
        self.base_url = get_api_url()
        self.session = None
        self._token_refresh_lock = asyncio.Lock()
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "bonito-cli/0.1.0"
        }
        
        api_key = get_api_key()
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        
        return headers
    
    async def _ensure_session(self):
        """Ensure HTTP session exists."""
        if self.session is None:
            self.session = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,
                follow_redirects=True
            )
    
    async def _refresh_token(self) -> bool:
        """Refresh access token using refresh token."""
        refresh_token = get_refresh_token()
        if not refresh_token:
            return False
        
        async with self._token_refresh_lock:
            try:
                await self._ensure_session()
                response = await self.session.post(
                    "/api/auth/refresh",
                    json={"refresh_token": refresh_token},
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    credentials = load_credentials()
                    credentials.update({
                        "access_token": data["access_token"],
                        "refresh_token": data.get("refresh_token", refresh_token),
                        "token_type": data.get("token_type", "bearer"),
                        "refreshed_at": datetime.now().isoformat()
                    })
                    save_credentials(credentials)
                    return True
            except Exception as e:
                console.print(f"[red]Token refresh failed: {e}[/red]")
        
        return False
    
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        stream: bool = False
    ) -> Union[Dict, httpx.Response]:
        """Make authenticated HTTP request with token refresh."""
        await self._ensure_session()
        
        url = endpoint if endpoint.startswith("http") else f"/api{endpoint}"
        headers = self._get_headers()
        
        try:
            response = await self.session.request(
                method=method,
                url=url,
                json=data,
                params=params,
                headers=headers
            )
            
            # Handle token refresh for 401 errors
            if response.status_code == 401 and not stream:
                if await self._refresh_token():
                    # Retry with new token
                    headers = self._get_headers()
                    response = await self.session.request(
                        method=method,
                        url=url,
                        json=data,
                        params=params,
                        headers=headers
                    )
            
            # Return response object for streaming
            if stream:
                return response
            
            # Handle non-streaming responses
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    message = error_data.get("detail", error_data.get("message", f"HTTP {response.status_code}"))
                except:
                    message = f"HTTP {response.status_code}: {response.text[:200]}"
                
                if response.status_code == 401:
                    message = "Authentication failed. Run 'bonito auth login' first."
                
                raise APIError(message, response.status_code, error_data if 'error_data' in locals() else None)
            
            try:
                return response.json()
            except:
                return {"status": "success", "text": response.text}
        
        except httpx.RequestError as e:
            raise APIError(f"Request failed: {e}")
    
    # Sync wrappers for CLI commands
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Sync GET request."""
        return asyncio.run(self._request("GET", endpoint, params=params))
    
    def post(self, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Sync POST request."""
        return asyncio.run(self._request("POST", endpoint, data=data))
    
    def put(self, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Sync PUT request."""
        return asyncio.run(self._request("PUT", endpoint, data=data))
    
    def delete(self, endpoint: str) -> Dict:
        """Sync DELETE request."""
        return asyncio.run(self._request("DELETE", endpoint))
    
    async def stream_post(self, endpoint: str, data: Optional[Dict] = None) -> httpx.Response:
        """Async streaming POST request."""
        return await self._request("POST", endpoint, data=data, stream=True)
    
    def close(self):
        """Close HTTP session."""
        if self.session:
            asyncio.run(self.session.aclose())
    
    # Authentication methods
    def login(self, api_key: str) -> Dict:
        """Login with API key."""
        try:
            # Test the API key
            response = self.post("/auth/login", {"api_key": api_key})
            
            # Save credentials
            credentials = {
                "access_token": response.get("access_token", api_key),
                "refresh_token": response.get("refresh_token"),
                "token_type": response.get("token_type", "bearer"),
                "api_key": api_key,
                "logged_in_at": datetime.now().isoformat()
            }
            save_credentials(credentials)
            
            return response
        except APIError as e:
            if e.status_code == 401:
                raise APIError("Invalid API key")
            raise
    
    def get_auth_status(self) -> Dict:
        """Get current authentication status."""
        return self.get("/auth/me")
    
    # Provider methods
    def list_providers(self) -> List[Dict]:
        """List connected providers."""
        return self.get("/providers/")
    
    def connect_provider(self, provider_data: Dict) -> Dict:
        """Connect a new provider."""
        return self.post("/providers/connect", provider_data)
    
    def verify_provider(self, provider_id: str) -> Dict:
        """Verify provider credentials."""
        return self.post(f"/providers/{provider_id}/verify")
    
    def delete_provider(self, provider_id: str) -> Dict:
        """Delete a provider."""
        return self.delete(f"/providers/{provider_id}")
    
    def get_provider_models(self, provider_id: str) -> List[Dict]:
        """Get models for a provider."""
        return self.get(f"/providers/{provider_id}/models")
    
    def get_provider_costs(self, provider_id: str, days: int = 30) -> Dict:
        """Get provider costs."""
        return self.get(f"/providers/{provider_id}/costs", {"days": days})
    
    # Model methods
    def list_models(self, provider: Optional[str] = None, enabled_only: bool = False, search: Optional[str] = None) -> List[Dict]:
        """List available models."""
        params = {}
        if provider:
            params["provider"] = provider
        if enabled_only:
            params["enabled_only"] = enabled_only
        if search:
            params["search"] = search
        
        return self.get("/models/", params)
    
    def get_model_info(self, model_id: str) -> Dict:
        """Get detailed model information."""
        return self.get(f"/models/{model_id}")
    
    def get_model_details(self, model_id: str) -> Dict:
        """Get model details (pricing, capabilities)."""
        return self.get(f"/models/{model_id}/details")
    
    def enable_model(self, model_id: str) -> Dict:
        """Enable a model."""
        return self.post(f"/models/{model_id}/activate")
    
    def enable_models_bulk(self, model_ids: List[str]) -> Dict:
        """Enable multiple models."""
        return self.post("/models/activate-bulk", {"model_ids": model_ids})
    
    def sync_models(self, provider_id: Optional[str] = None) -> Dict:
        """Sync model catalog."""
        data = {}
        if provider_id:
            data["provider_id"] = provider_id
        return self.post("/models/sync", data)
    
    # Chat/Playground methods
    def chat_completion(self, model_id: str, messages: List[Dict], **kwargs) -> Dict:
        """Get chat completion from model."""
        data = {
            "messages": messages,
            **kwargs
        }
        return self.post(f"/models/{model_id}/playground", data)
    
    async def stream_chat_completion(self, model_id: str, messages: List[Dict], **kwargs):
        """Stream chat completion from model."""
        data = {
            "messages": messages,
            "stream": True,
            **kwargs
        }
        response = await self.stream_post(f"/models/{model_id}/playground", data)
        
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                chunk = line[6:]  # Remove "data: " prefix
                if chunk.strip() == "[DONE]":
                    break
                try:
                    yield json.loads(chunk)
                except json.JSONDecodeError:
                    continue
    
    def compare_models(self, model_ids: List[str], prompt: str, **kwargs) -> Dict:
        """Compare multiple models."""
        data = {
            "model_ids": model_ids,
            "prompt": prompt,
            **kwargs
        }
        return self.post("/models/compare", data)
    
    # Gateway methods
    def get_gateway_keys(self) -> List[Dict]:
        """List gateway API keys."""
        return self.get("/gateway/keys")
    
    def create_gateway_key(self, name: Optional[str] = None) -> Dict:
        """Create new gateway API key."""
        data = {}
        if name:
            data["name"] = name
        return self.post("/gateway/keys", data)
    
    def revoke_gateway_key(self, key_id: str) -> Dict:
        """Revoke a gateway key."""
        return self.delete(f"/gateway/keys/{key_id}")
    
    def get_gateway_logs(self, limit: int = 50, model: Optional[str] = None) -> List[Dict]:
        """Get gateway logs."""
        params = {"limit": limit}
        if model:
            params["model"] = model
        return self.get("/gateway/logs", params)
    
    def get_gateway_config(self) -> Dict:
        """Get gateway configuration."""
        return self.get("/gateway/config")
    
    def update_gateway_config(self, config: Dict) -> Dict:
        """Update gateway configuration."""
        return self.put("/gateway/config", config)
    
    # Analytics methods
    def get_analytics_overview(self) -> Dict:
        """Get analytics overview."""
        return self.get("/analytics/overview")
    
    def get_analytics_usage(self, period: str = "week") -> Dict:
        """Get usage analytics."""
        return self.get("/analytics/usage", {"period": period})
    
    def get_analytics_costs(self, period: Optional[str] = None) -> Dict:
        """Get cost analytics."""
        params = {}
        if period:
            params["period"] = period
        return self.get("/analytics/costs", params)
    
    def get_analytics_trends(self) -> Dict:
        """Get trend analytics."""
        return self.get("/analytics/trends")
    
    def get_analytics_digest(self) -> Dict:
        """Get analytics digest."""
        return self.get("/analytics/digest")
    
    # Cost methods
    def get_costs(self, period: str = "monthly") -> Dict:
        """Get cost summary."""
        return self.get("/costs/", {"period": period})
    
    def get_cost_breakdown(self) -> Dict:
        """Get cost breakdown."""
        return self.get("/costs/breakdown")
    
    def get_cost_forecast(self) -> Dict:
        """Get cost forecast."""
        return self.get("/costs/forecast")
    
    def get_cost_recommendations(self) -> Dict:
        """Get cost recommendations."""
        return self.get("/costs/recommendations")
    
    # Deployment methods
    def list_deployments(self) -> List[Dict]:
        """List all deployments."""
        return self.get("/deployments/")
    
    def create_deployment(self, model_id: str, config: Dict) -> Dict:
        """Create a new deployment."""
        return self.post("/deployments/", {
            "model_id": model_id,
            "config": config
        })
    
    def get_deployment(self, deployment_id: str) -> Dict:
        """Get deployment details."""
        return self.get(f"/deployments/{deployment_id}")
    
    def delete_deployment(self, deployment_id: str) -> Dict:
        """Delete a deployment."""
        return self.delete(f"/deployments/{deployment_id}")
    
    def get_deployment_status(self, deployment_id: str) -> Dict:
        """Get deployment status."""
        return self.get(f"/deployments/{deployment_id}/status")


# Global API client instance
api = BonitoAPI()