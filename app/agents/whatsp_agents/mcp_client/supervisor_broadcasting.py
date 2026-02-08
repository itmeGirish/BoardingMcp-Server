"""
MCP Client Manager for broadcasting supervisor workflow

Manages connection to the Direct API MCP server (port 9002)
for template management, message sending, and analytics.
"""

import asyncio
from typing import Dict, Any, Optional
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from ....utils.whsp_onboarding_agent import parse_mcp_result, parse_mcp_result_with_debug
from ....config import logger


# ============================================
# CONFIGURATION
# ============================================

DIRECT_API_MCP_URL = "http://127.0.0.1:9002/mcp"
DIRECT_API_MCP_NAME = "DirectApiMCP"


# ============================================
# MCP CONNECTION MANAGER
# ============================================

class BroadcastMCPConnectionManager:
    """
    Singleton connection manager for Direct API MCP server.

    Provides:
    - Connection pooling and reuse
    - Tool caching
    - Thread-safe operations with async lock
    - Graceful shutdown

    Usage:
        tools = await BroadcastMCPConnectionManager.get_tools()
        result = await tools["get_templates"].ainvoke({...})
    """

    _client = None
    _session = None
    _session_context = None
    _tools: Optional[Dict[str, Any]] = None
    _lock = asyncio.Lock()

    @classmethod
    async def get_tools(cls) -> Dict[str, Any]:
        """
        Get Direct API MCP tools with connection reuse.

        Creates connection on first call, reuses thereafter.
        Thread-safe with async lock.
        """
        async with cls._lock:
            if cls._tools is None:
                logger.info("Creating new MCP connection to %s", DIRECT_API_MCP_URL)
                await cls._initialize_connection()
            return cls._tools

    @classmethod
    async def _initialize_connection(cls):
        """Initialize MCP connection and load tools."""
        try:
            cls._client = MultiServerMCPClient({
                DIRECT_API_MCP_NAME: {
                    "url": DIRECT_API_MCP_URL,
                    "transport": "streamable-http"
                }
            })

            cls._session_context = cls._client.session(DIRECT_API_MCP_NAME)
            cls._session = await cls._session_context.__aenter__()

            tools_list = await load_mcp_tools(cls._session)
            cls._tools = {t.name: t for t in tools_list}

            logger.info("Loaded %d Direct API MCP tools: %s",
                       len(cls._tools), list(cls._tools.keys()))

        except Exception as e:
            logger.error("Failed to initialize Direct API MCP: %s", e, exc_info=True)
            cls._tools = None
            raise

    @classmethod
    async def close(cls):
        """Close MCP connection gracefully."""
        async with cls._lock:
            if cls._session_context is not None:
                try:
                    await cls._session_context.__aexit__(None, None, None)
                    logger.info("Direct API MCP connection closed successfully")
                except Exception as e:
                    logger.error("Error closing Direct API MCP session: %s", e)
                finally:
                    cls._session_context = None
                    cls._session = None
                    cls._tools = None
                    cls._client = None

    @classmethod
    async def reset(cls):
        """Reset connection (useful for error recovery)."""
        await cls.close()
        logger.info("Direct API MCP connection reset")


# ============================================
# CLEANUP
# ============================================

def register_cleanup():
    """Register cleanup function to close MCP connection on shutdown."""
    import atexit
    atexit.register(lambda: asyncio.run(BroadcastMCPConnectionManager.close()))


register_cleanup()
