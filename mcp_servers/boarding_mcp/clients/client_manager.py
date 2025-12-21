"""
Client Manager for AiSensy Clients (GET, POST, and PATCH)

Provides safe client reuse across concurrent requests using a singleton pattern
with reference counting. Clients are kept alive as long as there are active
users and properly cleaned up when the application shuts down.
"""
import asyncio
from contextlib import asynccontextmanager
from typing import Optional, TypeVar, Generic, Type

from .get_clients import AiSensyGetClient
from .post_clients import AiSensyPostClient
from .patch_clients import AiSensyPatchClient
from app import logger

T = TypeVar("T", AiSensyGetClient, AiSensyPostClient, AiSensyPatchClient)


class BaseClientManager(Generic[T]):
    """
    Base class for managing shared client instances with reference counting.
    
    This ensures:
    1. Client is reused across concurrent requests (connection pooling)
    2. Client is not closed while other requests are using it
    3. Proper cleanup on application shutdown
    """
    
    _instance: Optional["BaseClientManager"] = None
    _client_class: Type[T] = None
    _client_name: str = "Base"
    
    def __init__(self):
        self._client: Optional[T] = None
        self._ref_count: int = 0
        self._client_lock: asyncio.Lock = asyncio.Lock()
    
    @classmethod
    def get_instance(cls) -> "BaseClientManager[T]":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    async def _ensure_client(self) -> T:
        """Ensure client exists and increment reference count."""
        async with self._client_lock:
            if self._client is None:
                logger.debug(f"Creating new AiSensy {self._client_name} client instance")
                self._client = self._client_class()
            
            self._ref_count += 1
            logger.debug(
                f"{self._client_name} client acquired. Active references: {self._ref_count}"
            )
            return self._client
    
    async def _release_client(self) -> None:
        """Decrement reference count. Client stays open for reuse."""
        async with self._client_lock:
            self._ref_count -= 1
            logger.debug(
                f"{self._client_name} client released. Active references: {self._ref_count}"
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
                        f"Closing {self._client_name} client with "
                        f"{self._ref_count} active references"
                    )
                logger.info(f"Closing AiSensy {self._client_name} client")
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
            logger.info(f"AiSensy {cls._client_name} client manager shutdown complete")


class AiSensyGetClientManager(BaseClientManager[AiSensyGetClient]):
    """Manager for AiSensy GET client."""
    
    _instance: Optional["AiSensyGetClientManager"] = None
    _client_class = AiSensyGetClient
    _client_name = "GET"


class AiSensyPostClientManager(BaseClientManager[AiSensyPostClient]):
    """Manager for AiSensy POST client."""
    
    _instance: Optional["AiSensyPostClientManager"] = None
    _client_class = AiSensyPostClient
    _client_name = "POST"


class AiSensyPatchClientManager(BaseClientManager[AiSensyPatchClient]):
    """Manager for AiSensy PATCH client."""
    
    _instance: Optional["AiSensyPatchClientManager"] = None
    _client_class = AiSensyPatchClient
    _client_name = "PATCH"


# Convenience context managers
@asynccontextmanager
async def get_aisensy_get_client():
    """
    Convenience context manager for getting the shared AiSensy GET client.
    
    Usage:
        async with get_aisensy_get_client() as client:
            result = await client.get_business_profile_by_id()
    """
    async with AiSensyGetClientManager.get_client() as client:
        yield client


@asynccontextmanager
async def get_aisensy_post_client():
    """
    Convenience context manager for getting the shared AiSensy POST client.
    
    Usage:
        async with get_aisensy_post_client() as client:
            result = await client.create_business_profile(...)
    """
    async with AiSensyPostClientManager.get_client() as client:
        yield client


@asynccontextmanager
async def get_aisensy_patch_client():
    """
    Convenience context manager for getting the shared AiSensy PATCH client.
    
    Usage:
        async with get_aisensy_patch_client() as client:
            result = await client.update_business_details(...)
    """
    async with AiSensyPatchClientManager.get_client() as client:
        yield client


# Backward compatibility alias
get_aisensy_client = get_aisensy_get_client


async def shutdown_all_clients() -> None:
    """
    Shutdown all client managers.
    Call this during application shutdown.
    
    Example usage with FastAPI:
        @app.on_event("shutdown")
        async def shutdown():
            await shutdown_all_clients()
    """
    await AiSensyGetClientManager.shutdown()
    await AiSensyPostClientManager.shutdown()
    await AiSensyPatchClientManager.shutdown()
    logger.info("All AiSensy client managers shutdown complete")