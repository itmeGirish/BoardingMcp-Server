"""
Client Manager for AiSensy Direct API Clients (GET, POST, DELETE, and PATCH)

Provides safe client reuse across concurrent requests using a singleton pattern
with reference counting. Clients are kept alive as long as there are active
users and properly cleaned up when the application shuts down.
"""
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, TypeVar, Generic, Type

from .direct_api_get_client import AiSensyDirectApiGetClient
from .direct_api_post_client import AiSensyDirectApiPostClient
from .direct_api_delete_client import AiSensyDirectApiDeleteClient
from .direct_api_patch_client import AiSensyDirectApiPatchClient
from app import logger

T = TypeVar(
    "T",
    AiSensyDirectApiGetClient,
    AiSensyDirectApiPostClient,
    AiSensyDirectApiDeleteClient,
    AiSensyDirectApiPatchClient
)


class BaseDirectApiClientManager(Generic[T]):
    """
    Base class for managing shared Direct API client instances with reference counting.
    
    This ensures:
    1. Client is reused across concurrent requests (connection pooling)
    2. Client is not closed while other requests are using it
    3. Proper cleanup on application shutdown
    """
    
    _instance: Optional["BaseDirectApiClientManager"] = None
    _client_class: Type[T] = None
    _client_name: str = "Base"
    
    def __init__(self):
        self._client: Optional[T] = None
        self._ref_count: int = 0
        self._client_lock: asyncio.Lock = asyncio.Lock()
    
    @classmethod
    def get_instance(cls) -> "BaseDirectApiClientManager[T]":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def _ensure_client(self) -> T:
        """Ensure client exists and increment reference count."""
        async with self._client_lock:
            if self._client is None:
                logger.debug(f"Creating new AiSensy Direct API {self._client_name} client instance")
                self._client = self._client_class()
            
            self._ref_count += 1
            logger.debug(
                f"Direct API {self._client_name} client acquired. Active references: {self._ref_count}"
            )
            return self._client
    
    async def _release_client(self) -> None:
        """Decrement reference count. Client stays open for reuse."""
        async with self._client_lock:
            self._ref_count -= 1
            logger.debug(
                f"Direct API {self._client_name} client released. Active references: {self._ref_count}"
            )
    
    async def close(self) -> None:
        """
        Force close the client. 
        Should only be called during application shutdown.
        """
        async with self._client_lock:
            if self._client is not None:
                if self._ref_count > 0:
                    logger.warning(
                        f"Closing Direct API {self._client_name} client with "
                        f"{self._ref_count} active references"
                    )
                logger.info(f"Closing AiSensy Direct API {self._client_name} client")
                await self._client.close()
                self._client = None
                self._ref_count = 0
    
    @classmethod
    @asynccontextmanager
    async def get_client(cls):
        """
        Context manager for safely acquiring and releasing the client.
        
        Yields:
            The shared client instance
        """
        manager = cls.get_instance()
        client = await manager._ensure_client()
        try:
            yield client
        finally:
            await manager._release_client()
    
    @classmethod
    async def shutdown(cls) -> None:
        """
        Shutdown the client manager and close the client.
        Call this during application shutdown.
        """
        if cls._instance is not None:
            await cls._instance.close()
            cls._instance = None
            logger.info(f"AiSensy Direct API {cls._client_name} client manager shutdown complete")


# ==================== GET CLIENT MANAGER ====================

class AiSensyDirectApiGetClientManager(BaseDirectApiClientManager[AiSensyDirectApiGetClient]):
    """Manager for AiSensy Direct API GET client."""
    
    _instance: Optional["AiSensyDirectApiGetClientManager"] = None
    _client_class = AiSensyDirectApiGetClient
    _client_name = "GET"


# ==================== POST CLIENT MANAGER ====================

class AiSensyDirectApiPostClientManager(BaseDirectApiClientManager[AiSensyDirectApiPostClient]):
    """Manager for AiSensy Direct API POST client."""
    
    _instance: Optional["AiSensyDirectApiPostClientManager"] = None
    _client_class = AiSensyDirectApiPostClient
    _client_name = "POST"


# ==================== DELETE CLIENT MANAGER ====================

class AiSensyDirectApiDeleteClientManager(BaseDirectApiClientManager[AiSensyDirectApiDeleteClient]):
    """Manager for AiSensy Direct API DELETE client."""
    
    _instance: Optional["AiSensyDirectApiDeleteClientManager"] = None
    _client_class = AiSensyDirectApiDeleteClient
    _client_name = "DELETE"


# ==================== PATCH CLIENT MANAGER ====================

class AiSensyDirectApiPatchClientManager(BaseDirectApiClientManager[AiSensyDirectApiPatchClient]):
    """Manager for AiSensy Direct API PATCH client."""
    
    _instance: Optional["AiSensyDirectApiPatchClientManager"] = None
    _client_class = AiSensyDirectApiPatchClient
    _client_name = "PATCH"


# ==================== CONVENIENCE CONTEXT MANAGERS ====================

@asynccontextmanager
async def get_direct_api_get_client():
    """
    Convenience context manager for getting the shared AiSensy Direct API GET client.
    
    Usage:
        async with get_direct_api_get_client() as client:
            result = await client.get_business_info()
    """
    async with AiSensyDirectApiGetClientManager.get_client() as client:
        yield client


@asynccontextmanager
async def get_direct_api_post_client():
    """
    Convenience context manager for getting the shared AiSensy Direct API POST client.
    
    Usage:
        async with get_direct_api_post_client() as client:
            result = await client.send_message(to="917089379345", message_type="text", text_body="Hello!")
    """
    async with AiSensyDirectApiPostClientManager.get_client() as client:
        yield client


@asynccontextmanager
async def get_direct_api_delete_client():
    """
    Convenience context manager for getting the shared AiSensy Direct API DELETE client.
    
    Usage:
        async with get_direct_api_delete_client() as client:
            result = await client.delete_template_by_name(template_name="my_template")
    """
    async with AiSensyDirectApiDeleteClientManager.get_client() as client:
        yield client


@asynccontextmanager
async def get_direct_api_patch_client():
    """
    Convenience context manager for getting the shared AiSensy Direct API PATCH client.
    
    Usage:
        async with get_direct_api_patch_client() as client:
            result = await client.update_profile(whatsapp_about="My Business")
    """
    async with AiSensyDirectApiPatchClientManager.get_client() as client:
        yield client


# ==================== SHUTDOWN FUNCTION ====================

async def shutdown_all_direct_api_clients() -> None:
    """
    Shutdown all Direct API client managers.
    Call this during application shutdown.
    
    Example usage with FastAPI:
        @app.on_event("shutdown")
        async def shutdown():
            await shutdown_all_direct_api_clients()
    """
    await AiSensyDirectApiGetClientManager.shutdown()
    await AiSensyDirectApiPostClientManager.shutdown()
    await AiSensyDirectApiDeleteClientManager.shutdown()
    await AiSensyDirectApiPatchClientManager.shutdown()
    logger.info("All AiSensy Direct API client managers shutdown complete")