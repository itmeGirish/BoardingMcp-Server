"""
GET client for AiSensy Direct APIs
"""
from typing import Dict, Any, Optional
import aiohttp

from .direct_api_base_client import AiSensyDirectApiClient
from app import logger


class AiSensyDirectApiGetClient(AiSensyDirectApiClient):
    """Client for all GET operations on Direct APIs."""

    # ==================== WABA INFORMATION ====================

    async def get_business_info(self) -> Dict[str, Any]:
        """
        Fetch WABA business info from the AiSensy Direct API.
        
        Endpoint: GET /get-business-info

        Returns:
            Dict[str, Any]: A dictionary containing the business info
            as returned by the AiSensy API.
        """
        url = f"{self.BASE_URL}/get-business-info"
        logger.debug(f"Fetching business info from: {url}")

        try:
            
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched business info")
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


    async def get_fb_verification_status(self,jwt_token:str) -> Dict[str, Any]:
        """
        Fetch fb_verification_status from the AiSensy Direct API.
        
        Endpoint: GET /fb_verification_status

        Returns:
            Dict[str, Any]: A dictionary containing the business info
            as returned by the AiSensy API.
        """
        url = f"{self.BASE_URL}/fb-verification-status"
        logger.debug(f"Fetching business info from: {url}")

        try:
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {jwt_token}"
            }
            session = await self._get_session()
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fb-verification-status info")
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

            








    # ==================== TEMPLATES ====================

    async def get_templates(self) -> Dict[str, Any]:
        """
        Fetch all templates from the AiSensy Direct API.
        
        Endpoint: GET /get-templates

        Returns:
            Dict[str, Any]: A dictionary containing all templates
            as returned by the AiSensy API.
        """
        url = f"{self.BASE_URL}/get-templates"
        logger.debug(f"Fetching templates from: {url}")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched templates")
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

    async def get_template_by_id(self, template_id: str,token:str) -> Dict[str, Any]:
        """
        Fetch a specific template by ID from the AiSensy Direct API.
        
        Endpoint: GET /get-template/{templateId}

        Args:
            template_id: The template ID to fetch.

        Returns:
            Dict[str, Any]: A dictionary containing the template details
            as returned by the AiSensy API.
        """
        if not template_id:
            logger.error("Missing template_id parameter")
            return {
                "success": False,
                "error": "Missing required field: template_id"
            }

        url = f"{self.BASE_URL}/get-template/{template_id}"
        logger.debug(f"Fetching template from: {url}")

        try:
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }

            session = await self._get_session()
            async with session.get(url,headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully fetched template: {template_id}")
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

    # ==================== MEDIA ====================

    async def get_media_upload_session(self, upload_session_id: str) -> Dict[str, Any]:
        """
        Fetch media upload session status from the AiSensy Direct API.
        
        Endpoint: GET /media/session/{uploadSessionId}

        Args:
            upload_session_id: The upload session ID to fetch.

        Returns:
            Dict[str, Any]: A dictionary containing the upload session details
            as returned by the AiSensy API.
        """
        if not upload_session_id:
            logger.error("Missing upload_session_id parameter")
            return {
                "success": False,
                "error": "Missing required field: upload_session_id"
            }

        url = f"{self.BASE_URL}/media/session/{upload_session_id}"
        logger.debug(f"Fetching media upload session from: {url}")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully fetched media upload session: {upload_session_id}")
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

    # ==================== PROFILE ====================

    async def get_profile(self) -> Dict[str, Any]:
        """
        Fetch user profile from the AiSensy Direct API.
        
        Endpoint: GET /get-profile

        Returns:
            Dict[str, Any]: A dictionary containing the user profile
            as returned by the AiSensy API.
        """
        url = f"{self.BASE_URL}/get-profile"
        logger.debug(f"Fetching profile from: {url}")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched profile")
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

    # ==================== PHONE NUMBERS ====================

    async def get_phone_numbers(self) -> Dict[str, Any]:
        """
        Fetch all phone numbers from the AiSensy Direct API.
        
        Endpoint: GET /get-phone-numbers

        Returns:
            Dict[str, Any]: A dictionary containing all phone numbers
            as returned by the AiSensy API.
        """
        url = f"{self.BASE_URL}/get-phone-numbers"
        logger.debug(f"Fetching phone numbers from: {url}")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched phone numbers")
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

    async def get_phone_number(self) -> Dict[str, Any]:
        """
        Fetch the primary/default phone number from the AiSensy Direct API.
        
        Endpoint: GET /get-phone-number

        Returns:
            Dict[str, Any]: A dictionary containing the phone number details
            as returned by the AiSensy API.
        """
        url = f"{self.BASE_URL}/get-phone-number"
        logger.debug(f"Fetching phone number from: {url}")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched phone number")
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

    # ==================== DISPLAY NAME / VERIFICATION ====================

    async def get_display_name_status(self) -> Dict[str, Any]:
        """
        Fetch the display name status (FB verification status) from the AiSensy Direct API.
        
        Endpoint: GET /get-display-name-status

        Returns:
            Dict[str, Any]: A dictionary containing the display name status
            as returned by the AiSensy API.
        """
        url = f"{self.BASE_URL}/get-display-name-status"
        logger.debug(f"Fetching display name status from: {url}")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched display name status")
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

    # ==================== CATALOG ====================

    async def get_catalog(self) -> Dict[str, Any]:
        """
        Fetch the catalog from the AiSensy Direct API.
        
        Endpoint: GET /catalog

        Returns:
            Dict[str, Any]: A dictionary containing the catalog details
            as returned by the AiSensy API.
        """
        url = f"{self.BASE_URL}/catalog"
        logger.debug(f"Fetching catalog from: {url}")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched catalog")
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

    # ==================== PRODUCTS ====================

    async def get_products(self) -> Dict[str, Any]:
        """
        Fetch all products from the AiSensy Direct API.
        
        Endpoint: GET /product

        Returns:
            Dict[str, Any]: A dictionary containing all products
            as returned by the AiSensy API.
        """
        url = f"{self.BASE_URL}/product"
        logger.debug(f"Fetching products from: {url}")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched products")
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

    # ==================== WHATSAPP COMMERCE ====================

    async def get_whatsapp_commerce_settings(self) -> Dict[str, Any]:
        """
        Fetch WhatsApp commerce settings from the AiSensy Direct API.
        
        Endpoint: GET /whatsapp-commerce-settings

        Returns:
            Dict[str, Any]: A dictionary containing the WhatsApp commerce settings
            as returned by the AiSensy API.
        """
        url = f"{self.BASE_URL}/whatsapp-commerce-settings"
        logger.debug(f"Fetching WhatsApp commerce settings from: {url}")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched WhatsApp commerce settings")
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

    # ==================== QR CODES ====================

    async def get_qr_codes(self) -> Dict[str, Any]:
        """
        Fetch all QR codes from the AiSensy Direct API.
        
        Endpoint: GET /qr-codes

        Returns:
            Dict[str, Any]: A dictionary containing all QR codes
            as returned by the AiSensy API.
        """
        url = f"{self.BASE_URL}/qr-codes"
        logger.debug(f"Fetching QR codes from: {url}")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched QR codes")
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

    # ==================== ENCRYPTION ====================

    async def get_whatsapp_business_encryption(self) -> Dict[str, Any]:
        """
        Fetch WhatsApp business encryption settings from the AiSensy Direct API.
        
        Endpoint: GET /whatsapp-business-encryption

        Returns:
            Dict[str, Any]: A dictionary containing the WhatsApp business encryption settings
            as returned by the AiSensy API.
        """
        url = f"{self.BASE_URL}/whatsapp-business-encryption"
        logger.debug(f"Fetching WhatsApp business encryption from: {url}")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched WhatsApp business encryption")
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

    # ==================== FLOWS ====================

    async def get_flows(self) -> Dict[str, Any]:
        """
        Fetch all flows from the AiSensy Direct API.
        
        Endpoint: GET /flows

        Returns:
            Dict[str, Any]: A dictionary containing all flows
            as returned by the AiSensy API.
        """
        url = f"{self.BASE_URL}/flows"
        logger.debug(f"Fetching flows from: {url}")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched flows")
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

    async def get_flow_by_id(self, flow_id: str) -> Dict[str, Any]:
        """
        Fetch a specific flow by ID from the AiSensy Direct API.
        
        Endpoint: GET /flows/{flowId}

        Args:
            flow_id: The flow ID to fetch.

        Returns:
            Dict[str, Any]: A dictionary containing the flow details
            as returned by the AiSensy API.
        """
        if not flow_id:
            logger.error("Missing flow_id parameter")
            return {
                "success": False,
                "error": "Missing required field: flow_id"
            }

        url = f"{self.BASE_URL}/flows/{flow_id}"
        logger.debug(f"Fetching flow from: {url}")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully fetched flow: {flow_id}")
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

    async def get_flow_assets(self, flow_id: str) -> Dict[str, Any]:
        """
        Fetch assets for a specific flow from the AiSensy Direct API.
        
        Endpoint: GET /flows/{flowId}/assets

        Args:
            flow_id: The flow ID to fetch assets for.

        Returns:
            Dict[str, Any]: A dictionary containing the flow assets
            as returned by the AiSensy API.
        """
        if not flow_id:
            logger.error("Missing flow_id parameter")
            return {
                "success": False,
                "error": "Missing required field: flow_id"
            }

        url = f"{self.BASE_URL}/flows/{flow_id}/assets"
        logger.debug(f"Fetching flow assets from: {url}")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully fetched flow assets: {flow_id}")
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

    async def get_flow_web_preview(self, flow_id: str) -> Dict[str, Any]:
        """
        Fetch web preview for a specific flow from the AiSensy Direct API.
        
        Endpoint: GET /flows/{flowId}/web-preview

        Args:
            flow_id: The flow ID to fetch web preview for.

        Returns:
            Dict[str, Any]: A dictionary containing the flow web preview
            as returned by the AiSensy API.
        """
        if not flow_id:
            logger.error("Missing flow_id parameter")
            return {
                "success": False,
                "error": "Missing required field: flow_id"
            }

        url = f"{self.BASE_URL}/flows/{flow_id}/web-preview"
        logger.debug(f"Fetching flow web preview from: {url}")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully fetched flow web preview: {flow_id}")
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

    # ==================== PAYMENT CONFIGURATIONS ====================

    async def get_payment_configurations(self) -> Dict[str, Any]:
        """
        Fetch all payment configurations from the AiSensy Direct API.
        
        Endpoint: GET /payment_configurations

        Returns:
            Dict[str, Any]: A dictionary containing all payment configurations
            as returned by the AiSensy API.
        """
        url = f"{self.BASE_URL}/payment_configurations"
        logger.debug(f"Fetching payment configurations from: {url}")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched payment configurations")
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

    async def get_payment_configuration_by_name(self, configuration_name: str) -> Dict[str, Any]:
        """
        Fetch a specific payment configuration by name from the AiSensy Direct API.
        
        Endpoint: GET /payment_configuration/{configuration_name}

        Args:
            configuration_name: The payment configuration name to fetch.

        Returns:
            Dict[str, Any]: A dictionary containing the payment configuration details
            as returned by the AiSensy API.
        """
        if not configuration_name:
            logger.error("Missing configuration_name parameter")
            return {
                "success": False,
                "error": "Missing required field: configuration_name"
            }

        url = f"{self.BASE_URL}/payment_configuration/{configuration_name}"
        logger.debug(f"Fetching payment configuration from: {url}")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully fetched payment configuration: {configuration_name}")
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