"""
This is base clients for AISENSY
"""
import aiohttp
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from app import settings, logger


@dataclass
class AiSensyBaseClient:
    """Base client with shared functionality."""
    timeout: int = 30
    BASE_URL: str = field(default_factory=lambda: settings.BASE_URL)
    _session: Optional[aiohttp.ClientSession] = field(default=None, init=False, repr=False)
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create HTTP session."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "X-AiSensy-Partner-API-Key": settings.AiSensy_API_Key,
                }
            )
            logger.debug("New HTTP session created")
        return self._session
    
    async def close(self) -> None:
        """Close HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            logger.debug("Session closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    def _handle_error(self, status: int, error_text: str) -> Dict[str, Any]:
        """Handle error response."""
        logger.warning(f"API error: {status} - {error_text}")
        error_map = {
            400: "Bad request",
            401: "Invalid API key",
            404: "Not found",
            409: "Already exists",
            422: "Validation error",
            429: "Rate limit exceeded",
            500: "Server error",
            503: "Service unavailable"
        }
        return {
            "success": False,
            "error": error_map.get(status, f"HTTP {status}"),
            "status_code": status,
            "details": error_text,
        }