"""
MCP Tool: Start Migration

Starts migration by submitting Facebook access token for migration to partner.
"""
from typing import Dict, Any

from .. import mcp
from ...models import StartMigrationRequest
from ...clients import get_aisensy_post_client
from app import logger


@mcp.tool(
    name="start_migration",
    description=(
        "Starts migration by submitting Facebook access token for migration to partner. "
        "Requires assistant_id, target_id, country_code, and phone_number. "
        "Requires PARTNER_ID to be configured in settings."
    ),
    tags={
        "migration",
        "facebook",
        "whatsapp",
        "start",
        "post",
        "aisensy"
    },
    meta={
        "version": "1.0.0",
        "author": "AiSensy Team",
        "category": "Migration"
    }
)
async def start_migration(
    assistant_id: str,
    target_id: str,
    country_code: str,
    phone_number: str
) -> Dict[str, Any]:
    """
    Start migration to partner.
    
    Args:
        assistant_id: The assistant ID.
        target_id: The target ID for migration.
        country_code: Country code (e.g., "91" for India, "1" for US).
        phone_number: Phone number to migrate.
    
    Returns:
        Dict containing:
        - success (bool): Whether the operation was successful
        - data (dict): Migration response data if successful
        - error (str): Error message if unsuccessful
    """
    try:
        # Validate input using Pydantic model
        request = StartMigrationRequest(
            assistant_id=assistant_id,
            target_id=target_id,
            country_code=country_code,
            phone_number=phone_number
        )
        
        async with get_aisensy_post_client() as client:
            response = await client.start_migration(
                assistant_id=request.assistant_id,
                target_id=request.target_id,
                country_code=request.country_code,
                phone_number=request.phone_number
            )
            
            if response.get("success"):
                logger.info(
                    f"Successfully started migration for phone: "
                    f"+{request.country_code}{request.phone_number}"
                )
            else:
                logger.warning(
                    f"Failed to start migration: {response.get('error')}"
                )
            
            return response
        
    except ValueError as e:
        error_msg = f"Validation error: {str(e)}"
        logger.error(error_msg)
        return {
            "success": False,
            "error": error_msg
        }
        
    except Exception as e:
        error_msg = f"Unexpected error starting migration: {str(e)}"
        logger.exception(error_msg)
        return {
            "success": False,
            "error": error_msg
        }