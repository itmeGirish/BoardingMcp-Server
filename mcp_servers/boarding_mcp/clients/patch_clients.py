"""This is PATCH Aisensy Client"""

from typing import Dict, Any, Optional
import aiohttp
import asyncio

from .base_client import AiSensyBaseClient
from app import settings, logger


class AiSensyPatchClient(AiSensyBaseClient):
    """Client for all PATCH operations."""

    async def update_business_details(
        self,
        display_name: Optional[str] = None,
        company: Optional[str] = None,
        contact: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update business details in the AiSensy API.

        Args:
            display_name: Optional new display name for the business.
            company: Optional new company name.
            contact: Optional new contact number.

        Returns:
            Dict[str, Any]: A dictionary containing the updated business details 
            as returned by the AiSensy API.
        """
        if not settings.PARTNER_ID or not settings.BUSINESS_ID:
            logger.error("Missing PARTNER_ID or BUSINESS_ID in settings")
            return {
                "success": False,
                "error": "Missing required fields: partner_id and business_id"
            }

        # Build payload with only provided fields
        payload = {}
        if display_name is not None:
            payload["display_name"] = display_name
        if company is not None:
            payload["company"] = company
        if contact is not None:
            payload["contact"] = contact

        if not payload:
            logger.error("No fields provided to update")
            return {
                "success": False,
                "error": "No fields provided to update"
            }

        url = f"{self.BASE_URL}/partner/{settings.PARTNER_ID}/business/{settings.BUSINESS_ID}"
        logger.debug(f"Updating business details at: {url}")

        try:
            session = await self._get_session()
            async with session.patch(url, json=payload) as response:
                if response.status in (200, 201):
                    data = await response.json()
                    logger.info("Successfully updated business details")
                    return {"success": True, "data": data}

                error_text = await response.text()
                return self._handle_error(response.status, error_text)

        except aiohttp.ClientConnectorError:
            logger.error("Network connection error")
            return {"success": False, "error": "Network connection error"}
        except aiohttp.ClientTimeout:
            logger.error("Request timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.exception("Unexpected error")
            return {"success": False, "error": str(e)}




# async def main():
#     """Test all PATCH client methods."""
    
#     async with AiSensyPatchClient() as client:
        
#         # 1. Update Business Details
#         print("=" * 50)
#         print("1. Update Business Details")
#         print("=" * 50)
#         result = await client.update_business_details(
#             display_name="Akira",
#             company="Aisensy",
#             contact="918645614148"
#         )
#         print(result)
#         print()


# if __name__ == "__main__":
#     asyncio.run(main())