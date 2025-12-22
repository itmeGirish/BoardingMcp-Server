"""This is POST Aisensy Client"""

from typing import Dict, Any, Optional
import aiohttp
import asyncio

from .base_client import AiSensyBaseClient
from app import settings, logger


class AiSensyPostClient(AiSensyBaseClient):
    """Client for all POST operations."""

    async def create_business_profile(
        self,
        display_name: str,
        email: str,
        company: str,
        contact: str,
        timezone: str,
        currency: str,
        company_size: str,
        password: str
    ) -> Dict[str, Any]:
        """
        Create a new business profile in the AiSensy API.
        """
        if not settings.PARTNER_ID:
            logger.error("Missing PARTNER_ID in settings")
            return {
                "success": False,
                "error": "Missing required field: partner_id"
            }

        url = f"{self.BASE_URL}/partner/{settings.PARTNER_ID}/business"
        payload = {
            "display_name": display_name,
            "email": email,
            "company": company,
            "contact": contact,
            "timezone": timezone,
            "currency": currency,
            "companySize": company_size,
            "password": password
        }
        logger.debug(f"Creating business profile at: {url}")

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status in (200, 201):
                    data = await response.json()
                    logger.info("Successfully created business profile")
                    return {"success": True, "data": data}

                error_text = await response.text()
                return self._handle_error(response.status, error_text)

        except aiohttp.ClientConnectorError:
            logger.error("Network connection error")
            return {"success": False, "error": "Network connection error"}
        except asyncio.TimeoutError:  # FIXED: was aiohttp.ClientTimeout
            logger.error("Request timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.exception("Unexpected error")
            return {"success": False, "error": str(e)}

    async def create_project(self, name: str,business_id:str) -> Dict[str, Any]:
        """
        Create a new project in the AiSensy API.
        """
        if not settings.PARTNER_ID:
            logger.error("Missing PARTNER_ID")
            return {
                "success": False,
                "error": "Missing required fields: partner_id"
            }

        if not name:
            logger.error("Missing name parameter")
            return {
                "success": False,
                "error": "Missing required field: name"
            }

        url = f"{self.BASE_URL}/partner/{settings.PARTNER_ID}/business/{business_id}/project"
        payload = {"name": name}
        logger.debug(f"Creating project at: {url}")

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status in (200, 201):
                    data = await response.json()
                    logger.info("Successfully created project")
                    return {"success": True, "data": data}

                error_text = await response.text()
                return self._handle_error(response.status, error_text)

        except aiohttp.ClientConnectorError:
            logger.error("Network connection error")
            return {"success": False, "error": "Network connection error"}
        except asyncio.TimeoutError:  # FIXED
            logger.error("Request timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.exception("Unexpected error")
            return {"success": False, "error": str(e)}

    async def generate_embedded_signup_url(
        self,
        business_id: str,
        assistant_id: str,
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
        description: Optional[str] = ""
    ) -> Dict[str, Any]:
        """
        Generate an embedded signup URL for WhatsApp Business API (WABA).
        """
        if not settings.PARTNER_ID:
            logger.error("Missing PARTNER_ID in settings")
            return {
                "success": False,
                "error": "Missing required field: partner_id"
            }

        url = f"{self.BASE_URL}/partner/{settings.PARTNER_ID}/generate-waba-link"
        payload = {
            "businessId": business_id,
            "assistantId": assistant_id,
            "setup": {
                "business": {
                    "name": business_name,
                    "email": business_email,
                    "phone": {
                        "code": phone_code,
                        "number": phone_number
                    },
                    "website": website,
                    "address": {
                        "streetAddress1": street_address,
                        "city": city,
                        "state": state,
                        "zipPostal": zip_postal,
                        "country": country
                    },
                    "timezone": timezone
                },
                "phone": {
                    "displayName": display_name,
                    "category": category,
                    "description": description
                }
            }
        }
        logger.debug(f"Generating embedded signup URL at: {url}")

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status in (200, 201):
                    data = await response.json()
                    logger.info("Successfully generated embedded signup URL")
                    return {"success": True, "data": data}

                error_text = await response.text()
                return self._handle_error(response.status, error_text)

        except aiohttp.ClientConnectorError:
            logger.error("Network connection error")
            return {"success": False, "error": "Network connection error"}
        except asyncio.TimeoutError:  # FIXED
            logger.error("Request timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.exception("Unexpected error")
            return {"success": False, "error": str(e)}

    async def submit_waba_app_id(
        self,
        assistant_id: str,
        waba_app_id: str
    ) -> Dict[str, Any]:
        """
        Submit WABA App ID (Facebook Access Token) to the AiSensy API.
        """
        if not settings.PARTNER_ID:
            logger.error("Missing PARTNER_ID in settings")
            return {
                "success": False,
                "error": "Missing required field: partner_id"
            }

        if not assistant_id or not waba_app_id:
            logger.error("Missing assistant_id or waba_app_id parameter")
            return {
                "success": False,
                "error": "Missing required fields: assistant_id and waba_app_id"
            }

        url = f"{self.BASE_URL}/partner/{settings.PARTNER_ID}/submit-facebook-access-token"
        payload = {
            "assistantId": assistant_id,
            "wabaAppId": waba_app_id
        }
        logger.debug(f"Submitting WABA App ID at: {url}")

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status in (200, 201):
                    data = await response.json()
                    logger.info("Successfully submitted WABA App ID")
                    return {"success": True, "data": data}

                error_text = await response.text()
                return self._handle_error(response.status, error_text)

        except aiohttp.ClientConnectorError:
            logger.error("Network connection error")
            return {"success": False, "error": "Network connection error"}
        except asyncio.TimeoutError:  # FIXED
            logger.error("Request timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.exception("Unexpected error")
            return {"success": False, "error": str(e)}

    async def start_migration(
        self,
        assistant_id: str,
        target_id: str,
        country_code: str,
        phone_number: str
    ) -> Dict[str, Any]:
        """
        Start migration by submitting Facebook access token for migration to partner.
        """
        if not settings.PARTNER_ID:
            logger.error("Missing PARTNER_ID in settings")
            return {
                "success": False,
                "error": "Missing required field: partner_id"
            }

        if not assistant_id or not target_id or not country_code or not phone_number:
            logger.error("Missing required parameters for migration")
            return {
                "success": False,
                "error": "Missing required fields: assistant_id, target_id, country_code, phone_number"
            }

        url = f"{self.BASE_URL}/partner/{settings.PARTNER_ID}/submit-facebook-access-token-for-migration-to-partner"
        payload = {
            "assistantId": assistant_id,
            "targetId": target_id,
            "countryCode": country_code,
            "phoneNumber": phone_number
        }
        logger.debug(f"Starting migration at: {url}")

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status in (200, 201):
                    data = await response.json()
                    logger.info("Successfully started migration")
                    return {"success": True, "data": data}

                error_text = await response.text()
                return self._handle_error(response.status, error_text)

        except aiohttp.ClientConnectorError:
            logger.error("Network connection error")
            return {"success": False, "error": "Network connection error"}
        except asyncio.TimeoutError:  # FIXED
            logger.error("Request timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.exception("Unexpected error")
            return {"success": False, "error": str(e)}

    async def request_otp_for_verification(
        self,
        assistant_id: str,
        mode: str = "sms"
    ) -> Dict[str, Any]:
        """
        Request OTP for verification during migration.
        """
        if not settings.PARTNER_ID:
            logger.error("Missing PARTNER_ID in settings")
            return {
                "success": False,
                "error": "Missing required field: partner_id"
            }

        if not assistant_id:
            logger.error("Missing assistant_id parameter")
            return {
                "success": False,
                "error": "Missing required field: assistant_id"
            }

        url = f"{self.BASE_URL}/partner/{settings.PARTNER_ID}/request-otp-for-migration-to-partner"
        payload = {
            "assistantId": assistant_id,
            "mode": mode
        }
        logger.debug(f"Requesting OTP for verification at: {url}")

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status in (200, 201):
                    data = await response.json()
                    logger.info("Successfully requested OTP for verification")
                    return {"success": True, "data": data}

                error_text = await response.text()
                return self._handle_error(response.status, error_text)

        except aiohttp.ClientConnectorError:
            logger.error("Network connection error")
            return {"success": False, "error": "Network connection error"}
        except asyncio.TimeoutError:  # FIXED
            logger.error("Request timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.exception("Unexpected error")
            return {"success": False, "error": str(e)}

    async def verify_otp(
        self,
        assistant_id: str,
        otp: str
    ) -> Dict[str, Any]:
        """
        Verify OTP for migration to partner.
        """
        if not settings.PARTNER_ID:
            logger.error("Missing PARTNER_ID in settings")
            return {
                "success": False,
                "error": "Missing required field: partner_id"
            }

        if not assistant_id or not otp:
            logger.error("Missing assistant_id or otp parameter")
            return {
                "success": False,
                "error": "Missing required fields: assistant_id and otp"
            }

        url = f"{self.BASE_URL}/partner/{settings.PARTNER_ID}/validate-otp-for-migration-to-partner"
        payload = {
            "assistantId": assistant_id,
            "otp": otp
        }
        logger.debug(f"Verifying OTP at: {url}")

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status in (200, 201):
                    data = await response.json()
                    logger.info("Successfully verified OTP")
                    return {"success": True, "data": data}

                error_text = await response.text()
                return self._handle_error(response.status, error_text)

        except aiohttp.ClientConnectorError:
            logger.error("Network connection error")
            return {"success": False, "error": "Network connection error"}
        except asyncio.TimeoutError:  # FIXED
            logger.error("Request timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.exception("Unexpected error")
            return {"success": False, "error": str(e)}

    async def generate_embedded_fb_catalog_url(
        self,
        business_id: str,
        assistant_id: str
    ) -> Dict[str, Any]:
        """
        Generate an embedded Facebook Catalog connect URL.
        """
        if not settings.PARTNER_ID:
            logger.error("Missing PARTNER_ID in settings")
            return {
                "success": False,
                "error": "Missing required field: partner_id"
            }

        if not business_id or not assistant_id:
            logger.error("Missing business_id or assistant_id parameter")
            return {
                "success": False,
                "error": "Missing required fields: business_id and assistant_id"
            }

        url = f"{self.BASE_URL}/partner/{settings.PARTNER_ID}/generate-catalog-connect-link"
        payload = {
            "businessId": business_id,
            "assistantId": assistant_id
        }
        logger.debug(f"Generating embedded FB catalog URL at: {url}")

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status in (200, 201):
                    data = await response.json()
                    logger.info("Successfully generated embedded FB catalog URL")
                    return {"success": True, "data": data}

                error_text = await response.text()
                return self._handle_error(response.status, error_text)

        except aiohttp.ClientConnectorError:
            logger.error("Network connection error")
            return {"success": False, "error": "Network connection error"}
        except asyncio.TimeoutError:  # FIXED
            logger.error("Request timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.exception("Unexpected error")
            return {"success": False, "error": str(e)}

    async def generate_ctwa_ads_manager_dashboard_url(
        self,
        business_id: str,
        assistant_id: str,
        expires_in: int = 150000
    ) -> Dict[str, Any]:
        """
        Generate CTWA (Click-to-WhatsApp) Ads Manager Dashboard URL.
        """
        if not settings.PARTNER_ID:
            logger.error("Missing PARTNER_ID in settings")
            return {
                "success": False,
                "error": "Missing required field: partner_id"
            }

        if not business_id or not assistant_id:
            logger.error("Missing business_id or assistant_id parameter")
            return {
                "success": False,
                "error": "Missing required fields: business_id and assistant_id"
            }

        url = f"{self.BASE_URL}/partner/{settings.PARTNER_ID}/ads/generate-dashboard-link"
        payload = {
            "businessId": business_id,
            "assistantId": assistant_id,
            "expiresIn": expires_in
        }
        logger.debug(f"Generating CTWA Ads Manager Dashboard URL at: {url}")

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status in (200, 201):
                    data = await response.json()
                    logger.info("Successfully generated CTWA Ads Manager Dashboard URL")
                    return {"success": True, "data": data}

                error_text = await response.text()
                return self._handle_error(response.status, error_text)

        except aiohttp.ClientConnectorError:
            logger.error("Network connection error")
            return {"success": False, "error": "Network connection error"}
        except asyncio.TimeoutError:  # FIXED
            logger.error("Request timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.exception("Unexpected error")
            return {"success": False, "error": str(e)}