"""
MCP Client Manager for onboarding workflow

This module manages the connection to the MCP server and provides
async functions for calling MCP tools.

IMPORTANT: This is where data normalization happens!
- normalize_timezone: "Asia/Calcutta" → "Asia/Calcutta GMT+05:30"
- normalize_country_code: "India" → "IN"
- parse_mcp_result: Parse various MCP response formats

Why here and not in states.py?
- States are pure TypedDict (no logic)
- Normalization is for MCP's requirements (belongs in MCP layer)
- Clean separation: states = structure, mcp_client = transformation

CRITICAL FIX: Imports are at module level to avoid blocking in ASGI context!
"""

import asyncio
import logging
from typing import Dict, Any, Optional

# CRITICAL: Import at MODULE level, not inside async functions!
# This prevents blocking file I/O in ASGI context
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools

# Import utils for data transformation (ONLY imported here!)
from ...utils.whsp_onboarding_agent import normalize_timezone, normalize_country_code, parse_mcp_result

from ...config import logger


# ============================================
# CONFIGURATION
# ============================================

MCP_SERVER_URL = "http://127.0.0.1:9001/mcp"
MCP_SERVER_NAME = "FormsMCP"


# ============================================
# MCP CONNECTION MANAGER
# ============================================

class MCPConnectionManager:
    """
    Singleton connection manager for MCP server.
    
    Provides:
    - Connection pooling and reuse
    - Tool caching
    - Thread-safe operations
    - Graceful shutdown
    
    Usage:
        tools = await MCPConnectionManager.get_tools()
        result = await tools["create_business_profile"].ainvoke({...})
    """
    
    _client = None
    _session = None
    _tools: Optional[Dict[str, Any]] = None
    _lock = asyncio.Lock()
    
    @classmethod
    async def get_tools(cls) -> Dict[str, Any]:
        """
        Get MCP tools with connection reuse.
        
        Creates connection on first call, reuses thereafter.
        Thread-safe with async lock.
        
        Returns:
            Dictionary mapping tool names to tool objects
        
        Raises:
            Exception: If connection to MCP server fails
        """
        async with cls._lock:
            if cls._tools is None:
                logger.info("Creating new MCP connection to %s", MCP_SERVER_URL)
                await cls._initialize_connection()
            
            return cls._tools
    
    @classmethod
    async def _initialize_connection(cls):
        """
        Initialize MCP connection and load tools.
        
        IMPORTANT: All imports are at module level to avoid blocking!
        """
        try:
            # No imports here! They're at module level
            cls._client = MultiServerMCPClient({
                MCP_SERVER_NAME: {
                    "url": MCP_SERVER_URL,
                    "transport": "streamable-http"
                }
            })
            
            # Create session
            cls._session = cls._client.session(MCP_SERVER_NAME)
            session_obj = await cls._session.__aenter__()
            
            # Load tools once
            tools_list = await load_mcp_tools(session_obj)
            cls._tools = {t.name: t for t in tools_list}
            
            logger.info("Successfully loaded %d MCP tools: %s", 
                       len(cls._tools), 
                       list(cls._tools.keys()))
            
        except Exception as e:
            logger.error("Failed to initialize MCP connection: %s", e, exc_info=True)
            cls._tools = None
            raise
    
    @classmethod
    async def close(cls):
        """Close MCP connection gracefully"""
        async with cls._lock:
            if cls._session:
                try:
                    # Properly close the session with async context manager
                    await cls._session.__aexit__(None, None, None)
                    logger.info("MCP connection closed successfully")
                except Exception as e:
                    logger.error("Error closing MCP session: %s", e)
                finally:
                    cls._session = None
                    cls._tools = None
                    cls._client = None
                    
                    # Also close the client if it has a close method
                    if cls._client and hasattr(cls._client, 'close'):
                        try:
                            await cls._client.close()
                        except:
                            pass
    
    @classmethod
    async def reset(cls):
        """Reset connection (useful for testing or error recovery)"""
        await cls.close()
        logger.info("MCP connection reset")


# ============================================
# MCP OPERATIONS
# ============================================

async def create_business_profile(
    user_id: str,
    display_name: str,
    email: str,
    company: str,
    contact: str,
    timezone: str,
    currency: str,
    company_size: str,
    password: str,
    onboarding_id: str
) -> Dict[str, Any]:
    """
    Create business profile via MCP.
    
    Args:
        user_id: User's unique identifier
        display_name: User's display name
        email: User's email address
        company: Company name
        contact: Contact number
        timezone: Timezone (will be normalized)
        currency: Currency code (e.g., "INR")
        company_size: Company size category
        password: User password
        onboarding_id: Onboarding session identifier
    
    Returns:
        MCP result dictionary
    
    Raises:
        Exception: If MCP call fails
    """
    try:
        tools = await MCPConnectionManager.get_tools()
        create_business_tool = tools["create_business_profile"]
        
        # Normalize timezone
        normalized_timezone = normalize_timezone(timezone)
        logger.debug("Creating business profile with timezone: %s → %s", 
                    timezone, normalized_timezone)
        
        result = await create_business_tool.ainvoke({
            "user_id": user_id,
            "display_name": display_name,
            "email": email,
            "company": company,
            "contact": contact,
            "timezone": normalized_timezone,
            "currency": currency,
            "company_size": company_size,
            "password": password,
            "onboarding_id": onboarding_id
        })
        
        parsed_result = parse_mcp_result(result)
        logger.info("Business profile created: %s", parsed_result.get("status", "unknown"))
        return parsed_result
        
    except Exception as e:
        logger.error("MCP create_business_profile error: %s", e, exc_info=True)
        return {"error": str(e), "status": "failed"}


async def create_project(
    user_id: str,
    name: str
) -> Dict[str, Any]:
    """
    Create project via MCP.
    
    Args:
        user_id: User's unique identifier
        name: Project name
    
    Returns:
        MCP result dictionary
    
    Raises:
        Exception: If MCP call fails
    """
    try:
        tools = await MCPConnectionManager.get_tools()
        create_project_tool = tools["create_project"]
        
        logger.debug("Creating project: %s for user: %s", name, user_id)
        
        result = await create_project_tool.ainvoke({
            "user_id": user_id,
            "name": name
        })
        
        parsed_result = parse_mcp_result(result)
        logger.info("Project created: %s", parsed_result.get("status", "unknown"))
        return parsed_result
        
    except Exception as e:
        logger.error("MCP create_project error: %s", e, exc_info=True)
        return {"error": str(e), "status": "failed"}


async def generate_embedded_signup_url(
    user_id: str,
    business_name: str,
    business_email: str,
    phone_code: int,
    phone_number: str,
    website: str,
    street_address: str,
    city: str,
    state: str,
    zip_postal: str,
    country: str,
    timezone: str,
    display_name: str,
    category: str,
    description: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generate embedded signup URL via MCP.
    
    Args:
        user_id: User's unique identifier
        business_name: Business name
        business_email: Business email address
        phone_code: Phone country code (e.g., 91)
        phone_number: Full phone number (e.g., "+919876543210")
        website: Business website URL
        street_address: Street address
        city: City
        state: State/Province
        zip_postal: ZIP or postal code
        country: Country (will be normalized to 2-char code)
        timezone: Timezone (will be normalized)
        display_name: Display name
        category: Business category
        description: Optional business description
    
    Returns:
        MCP result dictionary with signup URL
    
    Raises:
        Exception: If MCP call fails
    """
    try:
        tools = await MCPConnectionManager.get_tools()
        embedded_signup_tool = tools["generate_embedded_signup_url"]
        
        # Normalize timezone and country
        normalized_timezone = normalize_timezone(timezone)
        normalized_country = normalize_country_code(country)
        
        logger.debug("Generating embedded signup URL:")
        logger.debug("  Timezone: %s → %s", timezone, normalized_timezone)
        logger.debug("  Country: %s → %s", country, normalized_country)
        
        result = await embedded_signup_tool.ainvoke({
            "user_id": user_id,
            "business_name": business_name,
            "business_email": business_email,
            "phone_code": phone_code,
            "phone_number": phone_number,
            "website": website,
            "street_address": street_address,
            "city": city,
            "state": state,
            "zip_postal": zip_postal,
            "country": normalized_country,
            "timezone": normalized_timezone,
            "display_name": display_name,
            "category": category,
            "description": description
        })
        
        parsed_result = parse_mcp_result(result)
        logger.info("Embedded signup URL generated: %s", 
                   parsed_result.get("status", "unknown"))
        return parsed_result
        
    except Exception as e:
        logger.error("MCP generate_embedded_signup_url error: %s", e, exc_info=True)
        return {"error": str(e), "status": "failed"}


# ============================================
# CLEANUP
# ============================================

def register_cleanup():
    """Register cleanup function to close MCP connection on shutdown"""
    import atexit
    atexit.register(lambda: asyncio.run(MCPConnectionManager.close()))


# Auto-register cleanup
register_cleanup()