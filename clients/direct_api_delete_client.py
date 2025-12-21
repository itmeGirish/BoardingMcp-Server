"""
DELETE client for AiSensy Direct APIs
"""
from typing import Dict, Any
import aiohttp

from .direct_api_base_client import AiSensyDirectApiClient
from app import logger


class AiSensyDirectApiDeleteClient(AiSensyDirectApiClient):
    """Client for all DELETE operations on Direct APIs."""

    # ==================== 1. DELETE WA TEMPLATE BY ID ====================

    async def delete_wa_template_by_id(self, template_id: str) -> Dict[str, Any]:
        """
        Delete WA Template by ID.
        
        Endpoint: DELETE /wa_template

        Args:
            template_id: The template ID to delete.

        Returns:
            Dict[str, Any]: A dictionary containing the response
            as returned by the AiSensy API.
        """
        if not template_id:
            logger.error("Missing template_id parameter")
            return {
                "success": False,
                "error": "Missing required field: template_id"
            }

        url = f"{self.BASE_URL}/wa_template"
        params = {"templateId": template_id}
        logger.debug(f"Deleting WA template by ID: {template_id}")

        try:
            session = await self._get_session()
            async with session.delete(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully deleted WA template by ID: {template_id}")
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

    # ==================== 2. DELETE WA TEMPLATE BY NAME ====================

    async def delete_wa_template_by_name(self, template_name: str) -> Dict[str, Any]:
        """
        Delete WA Template by Name.
        
        Endpoint: DELETE /wa_template/{template_name}

        Args:
            template_name: The template name to delete.

        Returns:
            Dict[str, Any]: A dictionary containing the response
            as returned by the AiSensy API.
        """
        if not template_name:
            logger.error("Missing template_name parameter")
            return {
                "success": False,
                "error": "Missing required field: template_name"
            }

        url = f"{self.BASE_URL}/wa_template/{template_name}"
        logger.debug(f"Deleting WA template by name: {template_name}")

        try:
            session = await self._get_session()
            async with session.delete(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully deleted WA template by name: {template_name}")
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

    # ==================== 3. DELETE MEDIA BY ID ====================

    async def delete_media_by_id(self, media_id: str) -> Dict[str, Any]:
        """
        Delete Media by ID.
        
        Endpoint: DELETE /media

        Args:
            media_id: The media ID to delete.

        Returns:
            Dict[str, Any]: A dictionary containing the response
            as returned by the AiSensy API.
        """
        if not media_id:
            logger.error("Missing media_id parameter")
            return {
                "success": False,
                "error": "Missing required field: media_id"
            }

        url = f"{self.BASE_URL}/media"
        params = {"mediaId": media_id}
        logger.debug(f"Deleting media by ID: {media_id}")

        try:
            session = await self._get_session()
            async with session.delete(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully deleted media by ID: {media_id}")
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

    # ==================== 4. DISCONNECT CATALOG ====================

    async def disconnect_catalog(self) -> Dict[str, Any]:
        """
        Disconnect Catalog.
        
        Endpoint: DELETE /disconnect-catalog

        Returns:
            Dict[str, Any]: A dictionary containing the response
            as returned by the AiSensy API.
        """
        url = f"{self.BASE_URL}/disconnect-catalog"
        logger.debug(f"Disconnecting catalog at: {url}")

        try:
            session = await self._get_session()
            async with session.delete(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully disconnected catalog")
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

    # ==================== 5. DELETE A FLOW ====================

    async def delete_flow(self, flow_id: str) -> Dict[str, Any]:
        """
        Delete a Flow.
        
        Endpoint: DELETE /flows/{flowId}

        Args:
            flow_id: The flow ID to delete.

        Returns:
            Dict[str, Any]: A dictionary containing the response
            as returned by the AiSensy API.
        """
        if not flow_id:
            logger.error("Missing flow_id parameter")
            return {
                "success": False,
                "error": "Missing required field: flow_id"
            }

        url = f"{self.BASE_URL}/flows/{flow_id}"
        logger.debug(f"Deleting flow: {flow_id}")

        try:
            session = await self._get_session()
            async with session.delete(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully deleted flow: {flow_id}")
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