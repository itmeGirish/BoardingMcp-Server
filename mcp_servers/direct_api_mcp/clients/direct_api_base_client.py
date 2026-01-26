"""
Base client for AiSensy Direct APIs
"""
import aiohttp
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from app import settings, logger


@dataclass
class AiSensyDirectApiClient:
    """Base client for AiSensy Direct APIs with shared functionality."""
    
    timeout: int = 30
    BASE_URL: str = settings.Direct_BASE_URL
    _session: Optional[aiohttp.ClientSession] = field(default=None, init=False, repr=False)
    _token: str = field(default_factory=lambda: settings.AiSensy_API_Key)
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self._token}",
                }
            )
            logger.debug("New HTTP session created for Direct API")
        return self._session
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            logger.debug("Direct API session closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    def _handle_error(self, status: int, error_text: str) -> Dict[str, Any]:
        """Handle error response."""
        logger.warning(f"Direct API error: {status} - {error_text}")
        error_map = {
            400: "Bad request",
            401: "Invalid or expired token",
            403: "Forbidden - insufficient permissions",
            404: "Resource not found",
            409: "Conflict - resource already exists",
            422: "Validation error",
            429: "Rate limit exceeded",
            500: "Internal server error",
            502: "Bad gateway",
            503: "Service unavailable",
        }
        return {
            "success": False,
            "error": error_map.get(status, f"HTTP {status}"),
            "status_code": status,
            "details": error_text,
        }