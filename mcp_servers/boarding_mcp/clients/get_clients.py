"""This is GET Aisensy Client"""

from typing import Dict, Any, Optional
import aiohttp
import asyncio

from .base_client import AiSensyBaseClient
from app import settings, logger


class AiSensyGetClient(AiSensyBaseClient):
    """Client for all GET operations."""

    async def get_business_profile_by_id(self) -> Dict[str, Any]:
        """
        Fetch the business profile by id from the AiSensy API.

        Returns:
            Dict[str, Any]: A dictionary containing the business profile 
            details as returned by the AiSensy API.
        """
        if not settings.PARTNER_ID or not settings.BUSINESS_ID:
            logger.error("Missing PARTNER_ID or BUSINESS_ID in settings")
            return {
                "success": False,
                "error": "Missing required fields: partner_id and business_id"
            }

        url = f"{self.BASE_URL}/partner/{settings.PARTNER_ID}/business/{settings.BUSINESS_ID}"
        logger.debug(f"Fetching business profile from: {url}")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched business profile")
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

    async def get_all_business_profiles(self) -> Dict[str, Any]:
        """
        Fetch all business profiles for the partner from the AiSensy API.

        Returns:
            Dict[str, Any]: A dictionary containing all business profiles 
            as returned by the AiSensy API.
        """
        if not settings.PARTNER_ID:
            logger.error("Missing PARTNER_ID in settings")
            return {
                "success": False,
                "error": "Missing required field: partner_id"
            }

        url = f"{self.BASE_URL}/partner/{settings.PARTNER_ID}/business"
        logger.debug(f"Fetching all business profiles from: {url}")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched all business profiles")
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

    async def get_kyc_submission_status(self, project_id: str) -> Dict[str, Any]:
        """
        Fetch KYC submission status from the AiSensy API.

        Args:
            project_id: The project ID to check KYC status for.

        Returns:
            Dict[str, Any]: A dictionary containing the KYC submission status 
            as returned by the AiSensy API.
        """
        if not settings.PARTNER_ID:
            logger.error("Missing PARTNER_ID in settings")
            return {
                "success": False,
                "error": "Missing required field: partner_id"
            }

        if not project_id:
            logger.error("Missing project_id parameter")
            return {
                "success": False,
                "error": "Missing required field: project_id"
            }

        url = f"{self.BASE_URL}/partner/{settings.PARTNER_ID}/kyc/get-kyc-submission-status"
        params = {"projectId": project_id}
        logger.debug(f"Fetching KYC submission status from: {url} with params: {params}")

        try:
            session = await self._get_session()
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched KYC submission status")
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

    async def get_business_verification_status(self, project_id: str) -> Dict[str, Any]:
        """
        Fetch business verification status from the AiSensy API.

        Args:
            project_id: The project ID to check business verification status for.

        Returns:
            Dict[str, Any]: A dictionary containing the business verification status 
            as returned by the AiSensy API.
        """
        if not settings.PARTNER_ID:
            logger.error("Missing PARTNER_ID in settings")
            return {
                "success": False,
                "error": "Missing required field: partner_id"
            }

        if not project_id:
            logger.error("Missing project_id parameter")
            return {
                "success": False,
                "error": "Missing required field: project_id"
            }

        url = f"{self.BASE_URL}/partner/{settings.PARTNER_ID}/kyc/get-business-verification-status"
        params = {"projectId": project_id}
        logger.debug(f"Fetching business verification status from: {url} with params: {params}")

        try:
            session = await self._get_session()
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched business verification status")
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

    async def get_partner_details(self) -> Dict[str, Any]:
        """
        Fetch partner details from the AiSensy API.

        Returns:
            Dict[str, Any]: A dictionary containing the partner details 
            as returned by the AiSensy API.
        """
        if not settings.PARTNER_ID:
            logger.error("Missing PARTNER_ID in settings")
            return {
                "success": False,
                "error": "Missing required field: partner_id"
            }

        url = f"{self.BASE_URL}/partner/{settings.PARTNER_ID}"
        logger.debug(f"Fetching partner details from: {url}")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched partner details")
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

    async def get_wcc_usage_analytics(self, project_id: str) -> Dict[str, Any]:
        """
        Fetch WCC (WhatsApp Cloud Credits) usage analytics from the AiSensy API.

        Args:
            project_id: The project ID to get WCC analytics for.

        Returns:
            Dict[str, Any]: A dictionary containing the WCC usage analytics 
            as returned by the AiSensy API.
        """
        if not settings.PARTNER_ID:
            logger.error("Missing PARTNER_ID in settings")
            return {
                "success": False,
                "error": "Missing required field: partner_id"
            }

        if not project_id:
            logger.error("Missing project_id parameter")
            return {
                "success": False,
                "error": "Missing required field: project_id"
            }

        url = f"{self.BASE_URL}/partner/{settings.PARTNER_ID}/wcc-analytics"
        params = {"projectId": project_id}
        logger.debug(f"Fetching WCC usage analytics from: {url} with params: {params}")

        try:
            session = await self._get_session()
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched WCC usage analytics")
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

    async def get_billing_records(self, project_id: str) -> Dict[str, Any]:
        """
        Fetch billing records from the AiSensy API.

        Args:
            project_id: The project ID to get billing records for.

        Returns:
            Dict[str, Any]: A dictionary containing the billing records 
            as returned by the AiSensy API.
        """
        if not settings.PARTNER_ID:
            logger.error("Missing PARTNER_ID in settings")
            return {
                "success": False,
                "error": "Missing required field: partner_id"
            }

        if not project_id:
            logger.error("Missing project_id parameter")
            return {
                "success": False,
                "error": "Missing required field: project_id"
            }

        url = f"{self.BASE_URL}/partner/{settings.PARTNER_ID}/billings"
        params = {"projectId": project_id}
        logger.debug(f"Fetching billing records from: {url} with params: {params}")

        try:
            session = await self._get_session()
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched billing records")
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

    async def get_all_business_projects(
        self,
        fields: Optional[str] = None,
        additional_fields: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch all business projects from the AiSensy API.

        Args:
            fields: Optional fields parameter to filter response.
            additional_fields: Optional additional fields to include in response.

        Returns:
            Dict[str, Any]: A dictionary containing all business projects 
            as returned by the AiSensy API.
        """
        if not settings.PARTNER_ID or not settings.BUSINESS_ID:
            logger.error("Missing PARTNER_ID or BUSINESS_ID in settings")
            return {
                "success": False,
                "error": "Missing required fields: partner_id and business_id"
            }

        url = f"{self.BASE_URL}/partner/{settings.PARTNER_ID}/business/{settings.BUSINESS_ID}/project"
        params = {}
        if fields:
            params["fields"] = fields
        if additional_fields:
            params["additionalFields"] = additional_fields

        logger.debug(f"Fetching all business projects from: {url} with params: {params}")

        try:
            session = await self._get_session()
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched all business projects")
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

    async def get_project_by_id(self, project_id: str) -> Dict[str, Any]:
        """
        Fetch project details by ID from the AiSensy API.

        Args:
            project_id: The project ID to fetch details for.

        Returns:
            Dict[str, Any]: A dictionary containing the project details 
            as returned by the AiSensy API.
        """
        if not settings.PARTNER_ID:
            logger.error("Missing PARTNER_ID in settings")
            return {
                "success": False,
                "error": "Missing required field: partner_id"
            }

        if not project_id:
            logger.error("Missing project_id parameter")
            return {
                "success": False,
                "error": "Missing required field: project_id"
            }

        url = f"{self.BASE_URL}/partner/{settings.PARTNER_ID}/project/{project_id}"
        logger.debug(f"Fetching project by ID from: {url}")

        try:
            session = await self._get_session()
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched project by ID")
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
#     """Test all GET client methods."""
    
#     # Sample project_id for testing (replace with actual ID)
#     test_project_id = "test_project_123"
    
#     async with AiSensyGetClient() as client:
        
#         # 1. Get Business Profile by ID
#         print("=" * 50)
#         print("1. Get Business Profile by ID")
#         print("=" * 50)
#         result = await client.get_business_profile_by_id()
#         print(result)
#         print()

#         # 2. Get All Business Profiles
#         print("=" * 50)
#         print("2. Get All Business Profiles")
#         print("=" * 50)
#         result = await client.get_all_business_profiles()
#         print(result)
#         print()

#         # 3. Get KYC Submission Status
#         print("=" * 50)
#         print("3. Get KYC Submission Status")
#         print("=" * 50)
#         result = await client.get_kyc_submission_status(project_id=test_project_id)
#         print(result)
#         print()

#         # 4. Get Business Verification Status
#         print("=" * 50)
#         print("4. Get Business Verification Status")
#         print("=" * 50)
#         result = await client.get_business_verification_status(project_id=test_project_id)
#         print(result)
#         print()

#         # 5. Get Partner Details
#         print("=" * 50)
#         print("5. Get Partner Details")
#         print("=" * 50)
#         result = await client.get_partner_details()
#         print(result)
#         print()

#         # 6. Get WCC Usage Analytics
#         print("=" * 50)
#         print("6. Get WCC Usage Analytics")
#         print("=" * 50)
#         result = await client.get_wcc_usage_analytics(project_id=test_project_id)
#         print(result)
#         print()

#         # 7. Get Billing Records
#         print("=" * 50)
#         print("7. Get Billing Records")
#         print("=" * 50)
#         result = await client.get_billing_records(project_id=test_project_id)
#         print(result)
#         print()

#         # 8. Get All Business Projects
#         print("=" * 50)
#         print("8. Get All Business Projects")
#         print("=" * 50)
#         result = await client.get_all_business_projects(
#             fields="name,status",
#             additional_fields="metadata"
#         )
#         print(result)
#         print()

#         # 9. Get Project by ID
#         print("=" * 50)
#         print("9. Get Project by ID")
#         print("=" * 50)
#         result = await client.get_project_by_id(project_id=test_project_id)
#         print(result)
#         print()


# if __name__ == "__main__":
#     asyncio.run(main())