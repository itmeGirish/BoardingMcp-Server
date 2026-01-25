"""
Utility functions for onboarding workflow

This module contains helper functions for:
- Timezone normalization
- Country code conversion
- MCP result parsing with proper status handling
"""

import json
import logging
from typing import Dict, Any

from ..config import logger


# ============================================
# MODULE-LEVEL CONSTANTS
# ============================================

TIMEZONE_MAP = {
    "Asia/Calcutta": "Asia/Calcutta GMT+05:30",
    "Asia/Kolkata": "Asia/Calcutta GMT+05:30",
    "GMT+05:30": "Asia/Calcutta GMT+05:30",
    "GMT+5:30": "Asia/Calcutta GMT+05:30",
    "IST": "Asia/Calcutta GMT+05:30",
}

COUNTRY_MAP = {
    "India": "IN",
    "United States": "US",
    "United Kingdom": "GB",
    "Canada": "CA",
    "Australia": "AU",
    "Germany": "DE",
    "France": "FR",
    "Japan": "JP",
    "China": "CN",
    "Singapore": "SG",
    "Brazil": "BR",
    "Mexico": "MX",
    "Spain": "ES",
    "Italy": "IT",
    "Netherlands": "NL",
}


# ============================================
# NORMALIZATION FUNCTIONS
# ============================================

def normalize_timezone(timezone: str) -> str:
    """
    Normalize timezone to the format expected by MCP server.
    
    MCP server expects format: "Asia/Calcutta GMT+05:30"
    
    Args:
        timezone: Input timezone (e.g., "Asia/Calcutta", "IST", "GMT+05:30")
    
    Returns:
        Normalized timezone string
    
    Examples:
        >>> normalize_timezone("Asia/Calcutta")
        "Asia/Calcutta GMT+05:30"
        >>> normalize_timezone("IST")
        "Asia/Calcutta GMT+05:30"
        >>> normalize_timezone("Asia/Calcutta GMT+05:30")
        "Asia/Calcutta GMT+05:30"
    """
    # If already in correct format, return as-is
    if "GMT" in timezone and "/" in timezone:
        return timezone
    
    # Return mapped timezone or original if no mapping exists
    return TIMEZONE_MAP.get(timezone, timezone)


def normalize_country_code(country: str) -> str:
    """
    Normalize country name to ISO 2-character country code.
    
    MCP server expects 2-character codes like "IN", "US", etc.
    
    Args:
        country: Country name or code (e.g., "India", "US")
    
    Returns:
        ISO 2-character country code
    
    Examples:
        >>> normalize_country_code("India")
        "IN"
        >>> normalize_country_code("United States")
        "US"
        >>> normalize_country_code("IN")
        "IN"
    """
    # If already 2 characters, assume it's a code
    if len(country) == 2:
        return country.upper()
    
    # Return mapped code or original if no mapping exists
    return COUNTRY_MAP.get(country, country)


# ============================================
# PARSING FUNCTIONS
# ============================================

def parse_mcp_result(result: Any) -> Dict[str, Any]:
    """
    Parse MCP result into consistent dict format with proper status handling.
    
    Handles different MCP response formats:
    - Object with 'content' attribute
    - List with text items
    - Direct dict
    
    Also normalizes status keys:
    - "success": true → "status": "success"
    - "success": false → "status": "failed"
    - "error" present → "status": "failed"
    
    Args:
        result: Raw MCP result in any format
    
    Returns:
        Parsed result as dictionary with normalized "status" key
    
    Examples:
        >>> parse_mcp_result({"success": true})
        {"success": true, "status": "success"}
        >>> parse_mcp_result([{"type": "text", "text": '{"user_id": "123"}'}])
        {"user_id": "123", "status": "success"}
    """
    # Step 1: Extract the actual data from MCP wrapper
    if hasattr(result, 'content'):
        result_data = result.content
    else:
        result_data = result
    
    # Step 2: Handle list format from MCP
    if isinstance(result_data, list) and len(result_data) > 0:
        first_item = result_data[0]
        if isinstance(first_item, dict) and first_item.get('type') == 'text':
            text_content = first_item['text']
            try:
                result_data = json.loads(text_content)
            except (json.JSONDecodeError, TypeError):
                # If JSON parsing fails, treat as success with message
                result_data = {"message": text_content}
    
    # Step 3: Ensure we have a dict
    if not isinstance(result_data, dict):
        result_data = {"data": result_data}
    
    # Step 4: Normalize status key and add user-friendly message
    parsed = dict(result_data)  # Make a copy

    if "status" not in parsed:
        # Infer status from other fields
        # Check if error field exists AND has a truthy value (not None, not empty string)
        if parsed.get("error"):
            parsed["status"] = "failed"
        elif "success" in parsed:
            parsed["status"] = "success" if parsed["success"] else "failed"
        elif "user_id" in parsed or "business_id" in parsed or "project_id" in parsed:
            # If we have ID fields, assume success
            parsed["status"] = "success"
        else:
            # Default to success if no error indicators
            parsed["status"] = "success"

    # Step 5: Add user-friendly message field
    if "message" not in parsed:
        if parsed["status"] == "failed":
            # Extract error message from error field or details
            if parsed.get("error"):
                parsed["message"] = str(parsed["error"])
            elif parsed.get("details"):
                parsed["message"] = str(parsed["details"])
            else:
                parsed["message"] = "Operation failed"
        else:
            # Success message
            if "data" in parsed and isinstance(parsed["data"], dict):
                # Extract useful info from data for success message
                data = parsed["data"]
                if "display_name" in data:
                    parsed["message"] = f"Successfully created for {data['display_name']}"
                elif "name" in data:
                    parsed["message"] = f"Successfully created {data['name']}"
                elif "signup_url" in data:
                    parsed["message"] = f"Successfully generated signup URL"
                else:
                    parsed["message"] = "Operation completed successfully"
            else:
                parsed["message"] = "Operation completed successfully"

    return parsed


def parse_mcp_result_with_debug(result: Any) -> Dict[str, Any]:
    """
    Parse MCP result with debug logging.
    
    Use this version temporarily to see what MCP is actually returning.
    
    Args:
        result: Raw MCP result
    
    Returns:
        Parsed result with debug info logged
    """
    # Log raw result
    logger.info(f"📊 RAW MCP RESULT TYPE: {type(result)}")
    logger.info(f"📊 RAW MCP RESULT: {result}")
    
    if hasattr(result, 'content'):
        logger.info(f"📊 RESULT.CONTENT: {result.content}")
    
    # Parse
    parsed = parse_mcp_result(result)
    
    # Log parsed result
    logger.info(f"📊 PARSED RESULT KEYS: {list(parsed.keys())}")
    logger.info(f"📊 PARSED RESULT: {parsed}")
    
    return parsed