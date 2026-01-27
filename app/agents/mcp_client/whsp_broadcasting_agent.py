"""
MCP Client manager for broadcasting workflow

This module manages connections to the Direct API MCP server (port 9002)
for broadcasting-related operations like FB verification status checks.
"""

import asyncio
from typing import Optional, Dict, Any

from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from app.utils.whsp_onboarding_agent import parse_mcp_result_with_debug as parse_mcp_result
from ...config import logger

# MCP Server configuration
MCP_SERVER_URL = "http://127.0.0.1:9002/mcp"
MCP_SERVER_NAME = "DirectApiMCP"


class BroadcastingMCPConnectionManager:
    """
    Manages MCP connection for broadcasting operations.

    Uses the Direct API MCP server (port 9002) for:
    - FB verification status checks
    - Future broadcasting API calls
    """

    _instance: Optional["BroadcastingMCPConnectionManager"] = None
    _tools: Optional[Dict[str, Any]] = None
    _client: Optional[MultiServerMCPClient] = None
    _lock: asyncio.Lock = asyncio.Lock()

    @classmethod
    def get_instance(cls) -> "BroadcastingMCPConnectionManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def get_tools(self) -> Dict[str, Any]:
        async with self._lock:
            if self._tools is None:
                await self._initialize_connection()
            return self._tools

    async def _initialize_connection(self):
        logger.info("[BROADCASTING MCP] Initializing connection to %s", MCP_SERVER_URL)
        self._client = MultiServerMCPClient({
            MCP_SERVER_NAME: {
                "url": MCP_SERVER_URL,
                "transport": "streamable-http"
            }
        })

        async with self._client.session(MCP_SERVER_NAME) as session:
            mcp_tools_list = await load_mcp_tools(session)
            self._tools = {t.name: t for t in mcp_tools_list}
            logger.info("[BROADCASTING MCP] Loaded %d tools", len(self._tools))

    async def close(self):
        async with self._lock:
            if self._client is not None:
                self._client = None
                self._tools = None
                logger.info("[BROADCASTING MCP] Connection closed")

    @classmethod
    def reset(cls):
        cls._instance = None
        cls._tools = None
        cls._client = None


# ============================================
# MCP OPERATIONS
# ============================================

async def check_fb_verification_status(user_id: str) -> Dict[str, Any]:
    """
    Check FB verification status via MCP.

    Args:
        user_id: User ID to check verification for

    Returns:
        Dict with verification status result
    """
    logger.info("[BROADCASTING MCP] Checking FB verification for user_id: %s", user_id)

    client = MultiServerMCPClient({
        MCP_SERVER_NAME: {
            "url": MCP_SERVER_URL,
            "transport": "streamable-http"
        }
    })

    async with client.session(MCP_SERVER_NAME) as session:
        mcp_tools_list = await load_mcp_tools(session)
        mcp_tools = {t.name: t for t in mcp_tools_list}

        fb_status_tool = mcp_tools["fb_verification_status"]
        result = await fb_status_tool.ainvoke({"user_id": user_id})

        parsed = parse_mcp_result(result)
        logger.info("[BROADCASTING MCP] Verification result: %s", parsed.get('status', 'unknown'))
        return parsed


__all__ = [
    "BroadcastingMCPConnectionManager",
    "check_fb_verification_status",
]
