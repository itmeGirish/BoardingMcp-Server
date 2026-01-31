"""
POST client for AiSensy Direct APIs
"""
from typing import Any, Dict, List, Optional
import aiohttp

from .direct_api_base_client import AiSensyDirectApiClient
from app import logger


class AiSensyDirectApiPostClient(AiSensyDirectApiClient):
    """Client for all POST operations on Direct APIs."""

    # ==================== 1. AUTHENTICATION ====================

    async def regenerate_jwt_bearer_token(self,token:str, direct_api: bool = True) -> Dict[str, Any]:
        """
        Regenerate JWT Bearer Token to Access Direct-APIs.
        
        Endpoint: POST /users/regenrate-token

        Args:
            direct_api: Whether to use direct API. Defaults to True.

        Returns:
            Dict[str, Any]: A dictionary containing the new token details
            as returned by the AiSensy API.
        """
        url = f"{self.BASE_URL}/users/regenrate-token"
        payload = {"direct_api": direct_api}
        logger.debug(f"Regenerating JWT bearer token at: {url}")


        try:
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
            session = await self._get_session()
            async with session.post(url, json=payload,headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully regenerated JWT bearer token")
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

    # ==================== 2. ANALYTICS ====================

    async def get_waba_analytics(
        self,
        fields: str,
        start: int,
        end: int,
        granularity: str,
        country_codes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get WABA Analytics.
        
        Endpoint: POST /waba-analytics

        Args:
            fields: Analytics fields to fetch (e.g., "analytics").
            start: Start timestamp (Unix epoch).
            end: End timestamp (Unix epoch).
            granularity: Data granularity (e.g., "DAY", "MONTH").
            country_codes: Optional list of country codes to filter.

        Returns:
            Dict[str, Any]: A dictionary containing the WABA analytics
            as returned by the AiSensy API.
        """
        url = f"{self.BASE_URL}/waba-analytics"
        payload = {
            "fields": fields,
            "start": start,
            "end": end,
            "granularity": granularity
        }
        if country_codes:
            payload["country_codes"] = country_codes

        logger.debug(f"Fetching WABA analytics from: {url}")

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched WABA analytics")
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

    # ==================== 3. HEALTH STATUS ====================

    async def get_messaging_health_status(self, node_id: str) -> Dict[str, Any]:
        """
        Get Messaging Health Status.
        
        Endpoint: POST /health-status

        Args:
            node_id: The node ID to check health status for.

        Returns:
            Dict[str, Any]: A dictionary containing the health status
            as returned by the AiSensy API.
        """
        if not node_id:
            logger.error("Missing node_id parameter")
            return {
                "success": False,
                "error": "Missing required field: node_id"
            }

        url = f"{self.BASE_URL}/health-status"
        payload = {"nodeId": node_id}
        logger.debug(f"Fetching messaging health status from: {url}")

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully fetched messaging health status")
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

    # ==================== 4. SEND MESSAGE ====================

    async def send_message(
        self,
        to: str,
        message_type: str,
        jwt_token: str,
        text_body: Optional[str] = None,
        media_link: Optional[str] = None,
        media_caption: Optional[str] = None,
        media_filename: Optional[str] = None,
        template_name: Optional[str] = None,
        template_language_code: Optional[str] = None,
        template_language_policy: Optional[str] = "deterministic",
        template_components: Optional[List[Dict[str, Any]]] = None,
        interactive: Optional[Dict[str, Any]] = None,
        recipient_type: str = "individual",
    ) -> Dict[str, Any]:
        """
        Send Message.

        Endpoint: POST /messages

        Args:
            to: Recipient phone number (e.g., "917089379345").
            message_type: Type of message (e.g., "text", "image", "video", "audio", "document", "template").
            jwt_token: JWT bearer token for authorization.
            text_body: The message body text (required for type "text").
            media_link: URL of the media (required for image, video, audio, document).
            media_caption: Caption for the media (optional).
            media_filename: Filename for document type messages (optional).
            template_name: Template name (required for type "template").
            template_language_code: Template language code (required for type "template").
            template_language_policy: Template language policy (default: "deterministic").
            template_components: Template components list (optional for type "template").
            recipient_type: Type of recipient. Defaults to "individual".

        Returns:
            Dict[str, Any]: A dictionary containing the message response
            as returned by the AiSensy API.
        """
        if not to:
            logger.error("Missing required parameter: to")
            return {"success": False, "error": "Missing required field: to"}

        url = f"{self.BASE_URL}/messages"
        payload: Dict[str, Any] = {
            "to": to,
            "type": message_type,
            "recipient_type": recipient_type,
        }

        if message_type == "text":
            if not text_body:
                return {"success": False, "error": "Missing required field: text_body for text message"}
            payload["text"] = {"body": text_body}
        elif message_type in ("image", "video", "audio", "document"):
            if not media_link:
                return {"success": False, "error": f"Missing required field: media_link for {message_type} message"}
            media_obj: Dict[str, Any] = {"link": media_link}
            if media_caption:
                media_obj["caption"] = media_caption
            if message_type == "document" and media_filename:
                media_obj["filename"] = media_filename
            payload[message_type] = media_obj
        elif message_type == "template":
            if not template_name or not template_language_code:
                return {"success": False, "error": "Missing required fields: template_name and template_language_code for template message"}
            template_obj: Dict[str, Any] = {
                "name": template_name,
                "language": {
                    "policy": template_language_policy or "deterministic",
                    "code": template_language_code
                }
            }
            template_obj["components"] = template_components if template_components is not None else []
            payload["template"] = template_obj
        elif message_type == "interactive":
            if not interactive:
                return {"success": False, "error": "Missing required field: interactive for interactive message"}
            payload["interactive"] = interactive
        else:
            return {"success": False, "error": f"Unsupported message type: {message_type}"}

        logger.debug(f"Sending {message_type} message to: {to}")

        try:
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {jwt_token}"
            }

            session = await self._get_session()
            async with session.post(url, json=payload,headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully sent message to: {to}")
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

    # ==================== 5. SEND MARKETING LITE MESSAGE ====================

    async def send_marketing_lite_message(
        self,
        to: str,
        message_type: str,
        text_body: str,
        recipient_type: str = "individual"
    ) -> Dict[str, Any]:
        """
        Send Marketing Lite Message.
        
        Endpoint: POST /marketing_messages

        Args:
            to: Recipient phone number (e.g., "917089379345").
            message_type: Type of message (e.g., "text").
            text_body: The message body text.
            recipient_type: Type of recipient. Defaults to "individual".

        Returns:
            Dict[str, Any]: A dictionary containing the message response
            as returned by the AiSensy API.
        """
        if not to or not text_body:
            logger.error("Missing required parameters")
            return {
                "success": False,
                "error": "Missing required fields: to and text_body"
            }

        url = f"{self.BASE_URL}/marketing_messages"
        payload = {
            "to": to,
            "type": message_type,
            "recipient_type": recipient_type,
            "text": {
                "body": text_body
            }
        }
        logger.debug(f"Sending marketing lite message to: {to}")

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully sent marketing lite message to: {to}")
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

    # ==================== 6. MARK MESSAGE AS READ ====================

    async def mark_message_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        Mark message as read.
        
        Endpoint: POST /mark-read

        Args:
            message_id: The message ID to mark as read.

        Returns:
            Dict[str, Any]: A dictionary containing the response
            as returned by the AiSensy API.
        """
        if not message_id:
            logger.error("Missing message_id parameter")
            return {
                "success": False,
                "error": "Missing required field: message_id"
            }

        url = f"{self.BASE_URL}/mark-read"
        payload = {"messageId": message_id}
        logger.debug(f"Marking message as read: {message_id}")

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully marked message as read: {message_id}")
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

    # ==================== 7. SUBMIT WHATSAPP TEMPLATE MESSAGE ====================

    async def submit_whatsapp_template_message(
        self,
        name: str,
        category: str,
        language: str,
        token:str,
        components: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Submit WhatsApp Template Message.
        
        Endpoint: POST /wa_template

        Args:
            name: Template name.
            category: Template category (e.g., "MARKETING").
            language: Template language (e.g., "en").
            components: List of template components (HEADER, BODY, FOOTER, BUTTONS).

        Returns:
            Dict[str, Any]: A dictionary containing the created template
            as returned by the AiSensy API.
        """
        if not name or not category or not language or not components:
            logger.error("Missing required parameters")
            return {
                "success": False,
                "error": "Missing required fields: name, category, language, and components"
            }

        url = f"{self.BASE_URL}/wa_template"
        payload = {
            "name": name,
            "category": category,
            "language": language,
            "components": components
        }
        logger.debug(f"Submitting WhatsApp template: {name}")

        try:
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}"
            }
            session = await self._get_session()
            async with session.post(url, json=payload,headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully submitted WhatsApp template: {name}")
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

    # ==================== 8. EDIT TEMPLATE ====================

    async def edit_template(
        self,
        template_id: str,
        category: str,
        components: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Edit Template.
        
        Endpoint: POST /edit-template/{templateId}

        Args:
            template_id: The template ID to edit.
            category: Template category (e.g., "MARKETING").
            components: List of template components (HEADER, BODY, FOOTER, BUTTONS).

        Returns:
            Dict[str, Any]: A dictionary containing the updated template
            as returned by the AiSensy API.
        """
        if not template_id or not category or not components:
            logger.error("Missing required parameters")
            return {
                "success": False,
                "error": "Missing required fields: template_id, category, and components"
            }

        url = f"{self.BASE_URL}/edit-template/{template_id}"
        payload = {
            "category": category,
            "components": components
        }
        logger.debug(f"Editing template: {template_id}")

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully edited template: {template_id}")
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

    # ==================== 9. COMPARE TEMPLATE ====================

    async def compare_template(
        self,
        template_id: str,
        template_ids: List[int],
        start: int,
        end: int
    ) -> Dict[str, Any]:
        """
        Compare Template.
        
        Endpoint: POST /compare-template/{templateId}

        Args:
            template_id: The primary template ID for comparison.
            template_ids: List of template IDs to compare.
            start: Start timestamp (Unix epoch).
            end: End timestamp (Unix epoch).

        Returns:
            Dict[str, Any]: A dictionary containing the comparison results
            as returned by the AiSensy API.
        """
        if not template_id or not template_ids:
            logger.error("Missing required parameters")
            return {
                "success": False,
                "error": "Missing required fields: template_id and template_ids"
            }

        url = f"{self.BASE_URL}/compare-template/{template_id}"
        payload = {
            "templateIds": template_ids,
            "start": start,
            "end": end
        }
        logger.debug(f"Comparing template: {template_id}")

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully compared template: {template_id}")
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

    # ==================== 10. UPLOAD MEDIA ====================

    async def upload_media(self, file_path: str) -> Dict[str, Any]:
        """
        Upload Media.
        
        Endpoint: POST /media (multipart/form-data)

        Args:
            file_path: Path to the file to upload.

        Returns:
            Dict[str, Any]: A dictionary containing the upload response
            as returned by the AiSensy API.
        """
        if not file_path:
            logger.error("Missing file_path parameter")
            return {
                "success": False,
                "error": "Missing required field: file_path"
            }

        url = f"{self.BASE_URL}/media"
        logger.debug(f"Uploading media from: {file_path}")

        try:
            session = await self._get_session()
            data = aiohttp.FormData()
            data.add_field('file', open(file_path, 'rb'))

            async with session.post(url, data=data) as response:
                if response.status == 200:
                    resp_data = await response.json()
                    logger.info("Successfully uploaded media")
                    return {"success": True, "data": resp_data}

                error_text = await response.text()
                return self._handle_error(response.status, error_text)

        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return {"success": False, "error": f"File not found: {file_path}"}
        except aiohttp.ClientConnectorError:
            logger.error("Network connection error")
            return {"success": False, "error": "Network connection error"}
        except aiohttp.ClientTimeout:
            logger.error("Request timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.exception("Unexpected error")
            return {"success": False, "error": str(e)}

    # ==================== 11. RETRIEVE MEDIA BY ID ====================

    async def retrieve_media_by_id(self, media_id: str) -> Dict[str, Any]:
        """
        Retrieve Media by ID.
        
        Endpoint: POST /get-media

        Args:
            media_id: The media ID to fetch.

        Returns:
            Dict[str, Any]: A dictionary containing the media details
            as returned by the AiSensy API.
        """
        if not media_id:
            logger.error("Missing media_id parameter")
            return {
                "success": False,
                "error": "Missing required field: media_id"
            }

        url = f"{self.BASE_URL}/get-media"
        payload = {"id": media_id}
        logger.debug(f"Retrieving media: {media_id}")

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully retrieved media: {media_id}")
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

    # ==================== 12. CREATE UPLOAD SESSION ====================

    async def create_upload_session(
        self,
        file_name: str,
        file_length: str,
        file_type: str
    ) -> Dict[str, Any]:
        """
        Create Upload Session.
        
        Endpoint: POST /media/session

        Args:
            file_name: Name of the file to upload.
            file_length: Size of the file in bytes.
            file_type: MIME type of the file (e.g., "image/jpg").

        Returns:
            Dict[str, Any]: A dictionary containing the session details
            as returned by the AiSensy API.
        """
        if not file_name or not file_length or not file_type:
            logger.error("Missing required parameters")
            return {
                "success": False,
                "error": "Missing required fields: file_name, file_length, and file_type"
            }

        url = f"{self.BASE_URL}/media/session"
        payload = {
            "fileName": file_name,
            "fileLength": file_length,
            "fileType": file_type
        }
        logger.debug(f"Creating upload session for: {file_name}")

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully created upload session for: {file_name}")
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

    # ==================== 13. UPLOAD MEDIA TO SESSION ====================

    async def upload_media_to_session(
        self,
        upload_session_id: str,
        file_path: str,
        file_offset: int = 0
    ) -> Dict[str, Any]:
        """
        Upload Media to Session.
        
        Endpoint: POST /media/session/{uploadSessionId} (multipart/form-data)

        Args:
            upload_session_id: The upload session ID.
            file_path: Path to the file to upload.
            file_offset: Byte offset for resumable uploads. Defaults to 0.

        Returns:
            Dict[str, Any]: A dictionary containing the upload response
            as returned by the AiSensy API.
        """
        if not upload_session_id or not file_path:
            logger.error("Missing required parameters")
            return {
                "success": False,
                "error": "Missing required fields: upload_session_id and file_path"
            }

        url = f"{self.BASE_URL}/media/session/{upload_session_id}"
        logger.debug(f"Uploading media to session: {upload_session_id}")

        try:
            session = await self._get_session()
            data = aiohttp.FormData()
            data.add_field('file', open(file_path, 'rb'))
            data.add_field('fileOffset', str(file_offset))

            async with session.post(url, data=data) as response:
                if response.status == 200:
                    resp_data = await response.json()
                    logger.info(f"Successfully uploaded media to session: {upload_session_id}")
                    return {"success": True, "data": resp_data}

                error_text = await response.text()
                return self._handle_error(response.status, error_text)

        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return {"success": False, "error": f"File not found: {file_path}"}
        except aiohttp.ClientConnectorError:
            logger.error("Network connection error")
            return {"success": False, "error": "Network connection error"}
        except aiohttp.ClientTimeout:
            logger.error("Request timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.exception("Unexpected error")
            return {"success": False, "error": str(e)}

    # ==================== 14. CREATE CATALOG ====================

    async def create_catalog(
        self,
        jwt_token:str,
        name: str,
        vertical: str = "commerce",
        product_count: int = 0,
        feed_count: int = 1,
        default_image_url: Optional[str] = None,
        fallback_image_url: Optional[List[str]] = None,
        is_catalog_segment: bool = False,
        da_display_settings: Optional[Dict[str, Any]] = None,
        
    ) -> Dict[str, Any]:
        """
        Create Catalog.
        
        Endpoint: POST /catalog

        Args:
            name: Catalog name.
            vertical: Catalog vertical. Defaults to "commerce".
            product_count: Number of products. Defaults to 0.
            feed_count: Number of feeds. Defaults to 1.
            default_image_url: Default image URL.
            fallback_image_url: List of fallback image URLs.
            is_catalog_segment: Whether catalog is a segment. Defaults to False.
            da_display_settings: Display settings for dynamic ads.

        Returns:
            Dict[str, Any]: A dictionary containing the created catalog
            as returned by the AiSensy API.
        """
        if not name:
            logger.error("Missing name parameter")
            return {
                "success": False,
                "error": "Missing required field: name"
            }

        url = f"{self.BASE_URL}/catalog"
        payload = {
            "vertical": vertical,
            "name": name,
            "product_count": product_count,
            "feed_count": feed_count,
            "is_catalog_segment": is_catalog_segment
        }
        if default_image_url:
            payload["default_image_url"] = default_image_url
        if fallback_image_url:
            payload["fallback_image_url"] = fallback_image_url
        if da_display_settings:
            payload["da_display_settings"] = da_display_settings

        logger.debug(f"Creating catalog: {name}")

        try:
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {jwt_token}",
                "Content-Type": "application/json",
                
            }
            session = await self._get_session()
            async with session.post(url, json=payload,headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully created catalog: {name}")
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

    # ==================== 15. CONNECT CATALOG ====================

    async def connect_catalog(self, catalog_id: str) -> Dict[str, Any]:
        """
        Connect Catalog.
        
        Endpoint: POST /connect-catalog

        Args:
            catalog_id: The catalog ID to connect.

        Returns:
            Dict[str, Any]: A dictionary containing the response
            as returned by the AiSensy API.
        """
        if not catalog_id:
            logger.error("Missing catalog_id parameter")
            return {
                "success": False,
                "error": "Missing required field: catalog_id"
            }

        url = f"{self.BASE_URL}/connect-catalog"
        payload = {"catalogId": catalog_id}
        logger.debug(f"Connecting catalog: {catalog_id}")

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully connected catalog: {catalog_id}")
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

    # ==================== 16. CREATE PRODUCT ====================

    async def create_product(
        self,
        catalog_id: str,
        name: str,
        category: str,
        currency: str,
        image_url: str,
        price: str,
        retailer_id: str,
        description: Optional[str] = None,
        url: Optional[str] = None,
        brand: Optional[str] = None,
        sale_price: Optional[str] = None,
        sale_price_start_date: Optional[str] = None,
        sale_price_end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create Product.
        
        Endpoint: POST /product

        Args:
            catalog_id: The catalog ID to add product to.
            name: Product name.
            category: Product category.
            currency: Currency code (e.g., "INR").
            image_url: Product image URL.
            price: Product price.
            retailer_id: Retailer ID.
            description: Product description.
            url: Product URL.
            brand: Product brand.
            sale_price: Sale price.
            sale_price_start_date: Sale start date.
            sale_price_end_date: Sale end date.

        Returns:
            Dict[str, Any]: A dictionary containing the created product
            as returned by the AiSensy API.
        """
        if not catalog_id or not name or not category or not currency or not image_url or not price or not retailer_id:
            logger.error("Missing required parameters")
            return {
                "success": False,
                "error": "Missing required fields: catalog_id, name, category, currency, image_url, price, retailer_id"
            }

        url_endpoint = f"{self.BASE_URL}/product"
        payload = {
            "catalogId": catalog_id,
            "name": name,
            "category": category,
            "currency": currency,
            "image_url": image_url,
            "price": price,
            "retailer_id": retailer_id
        }
        if description:
            payload["description"] = description
        if url:
            payload["url"] = url
        if brand:
            payload["brand"] = brand
        if sale_price:
            payload["sale_price"] = sale_price
        if sale_price_start_date:
            payload["sale_price_start_date"] = sale_price_start_date
        if sale_price_end_date:
            payload["sale_price_end_date"] = sale_price_end_date

        logger.debug(f"Creating product: {name}")

        try:
            session = await self._get_session()
            async with session.post(url_endpoint, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully created product: {name}")
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

    # ==================== 17. SHOW / HIDE CATALOG ====================

    async def show_hide_catalog(
        self,
        enable_catalog: bool,
        enable_cart: bool
    ) -> Dict[str, Any]:
        """
        Show / Hide Catalog (Update WhatsApp Commerce Settings).
        
        Endpoint: POST /whatsapp-commerce-settings

        Args:
            enable_catalog: Whether to enable catalog.
            enable_cart: Whether to enable cart.

        Returns:
            Dict[str, Any]: A dictionary containing the updated settings
            as returned by the AiSensy API.
        """
        url = f"{self.BASE_URL}/whatsapp-commerce-settings"
        payload = {
            "enableCatalog": enable_catalog,
            "enableCart": enable_cart
        }
        logger.debug("Updating WhatsApp commerce settings (show/hide catalog)")

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully updated WhatsApp commerce settings")
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

    # ==================== 18. CREATE QR CODE & SHORT LINK ====================

    async def create_qr_code_and_short_link(
        self,
        prefilled_message: str,
        generate_qr_image: str = "SVG"
    ) -> Dict[str, Any]:
        """
        Create QR Code & Short Link.
        
        Endpoint: POST /qr-codes

        Args:
            prefilled_message: The prefilled message for the QR code.
            generate_qr_image: QR image format. Defaults to "SVG".

        Returns:
            Dict[str, Any]: A dictionary containing the created QR code
            as returned by the AiSensy API.
        """
        if not prefilled_message:
            logger.error("Missing prefilled_message parameter")
            return {
                "success": False,
                "error": "Missing required field: prefilled_message"
            }

        url = f"{self.BASE_URL}/qr-codes"
        payload = {
            "prefilledMessage": prefilled_message,
            "generateQrImage": generate_qr_image
        }
        logger.debug("Creating QR code and short link")

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully created QR code and short link")
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

    # ==================== 19. SET BUSINESS PUBLIC KEY ====================

    async def set_business_public_key(self, business_public_key: str) -> Dict[str, Any]:
        """
        Set Business Public Key.
        
        Endpoint: POST /whatsapp-business-encryption

        Args:
            business_public_key: The business public key (PEM format).

        Returns:
            Dict[str, Any]: A dictionary containing the response
            as returned by the AiSensy API.
        """
        if not business_public_key:
            logger.error("Missing business_public_key parameter")
            return {
                "success": False,
                "error": "Missing required field: business_public_key"
            }

        url = f"{self.BASE_URL}/whatsapp-business-encryption"
        payload = {"businessPublicKey": business_public_key}
        logger.debug("Setting business public key")

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully set business public key")
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

    # ==================== 20. CREATING A FLOW ====================

    async def create_flow(
        self,
        name: str,
        categories: List[str]
    ) -> Dict[str, Any]:
        """
        Creating a Flow.
        
        Endpoint: POST /flows

        Args:
            name: Flow name.
            categories: List of flow categories (e.g., ["APPOINTMENT_BOOKING"]).

        Returns:
            Dict[str, Any]: A dictionary containing the created flow
            as returned by the AiSensy API.
        """
        if not name or not categories:
            logger.error("Missing required parameters")
            return {
                "success": False,
                "error": "Missing required fields: name and categories"
            }

        url = f"{self.BASE_URL}/flows"
        payload = {
            "name": name,
            "categories": categories
        }
        logger.debug(f"Creating flow: {name}")

        try:
            session = await self._get_session()
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully created flow: {name}")
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

    # ==================== 21. UPDATING A FLOW'S FLOW JSON ====================

    async def update_flow_json(self, flow_id: str, file_path: str) -> Dict[str, Any]:
        """
        Updating a Flow's Flow JSON (Upload flow assets).
        
        Endpoint: POST /flows/{flowId}/assets (multipart/form-data)

        Args:
            flow_id: The flow ID to upload assets to.
            file_path: Path to the file to upload.

        Returns:
            Dict[str, Any]: A dictionary containing the upload response
            as returned by the AiSensy API.
        """
        if not flow_id or not file_path:
            logger.error("Missing required parameters")
            return {
                "success": False,
                "error": "Missing required fields: flow_id and file_path"
            }

        url = f"{self.BASE_URL}/flows/{flow_id}/assets"
        logger.debug(f"Updating flow JSON for: {flow_id}")

        try:
            session = await self._get_session()
            data = aiohttp.FormData()
            data.add_field('file', open(file_path, 'rb'))

            async with session.post(url, data=data) as response:
                if response.status == 200:
                    resp_data = await response.json()
                    logger.info(f"Successfully updated flow JSON for: {flow_id}")
                    return {"success": True, "data": resp_data}

                error_text = await response.text()
                return self._handle_error(response.status, error_text)

        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return {"success": False, "error": f"File not found: {file_path}"}
        except aiohttp.ClientConnectorError:
            logger.error("Network connection error")
            return {"success": False, "error": "Network connection error"}
        except aiohttp.ClientTimeout:
            logger.error("Request timeout")
            return {"success": False, "error": "Request timeout"}
        except Exception as e:
            logger.exception("Unexpected error")
            return {"success": False, "error": str(e)}

    # ==================== 22. PUBLISH FLOW ====================

    async def publish_flow(self, flow_id: str) -> Dict[str, Any]:
        """
        Publish Flow.
        
        Endpoint: POST /flows/{flowId}/publish

        Args:
            flow_id: The flow ID to publish.

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

        url = f"{self.BASE_URL}/flows/{flow_id}/publish"
        logger.debug(f"Publishing flow: {flow_id}")

        try:
            session = await self._get_session()
            async with session.post(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully published flow: {flow_id}")
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

    # ==================== 23. DEPRECATE FLOW ====================

    async def deprecate_flow(self, flow_id: str) -> Dict[str, Any]:
        """
        Deprecate Flow.
        
        Endpoint: POST /flows/{flowId}/deprecate

        Args:
            flow_id: The flow ID to deprecate.

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

        url = f"{self.BASE_URL}/flows/{flow_id}/deprecate"
        logger.debug(f"Deprecating flow: {flow_id}")

        try:
            session = await self._get_session()
            async with session.post(url) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully deprecated flow: {flow_id}")
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

    # ==================== 24. CREATE PAYMENT CONFIGURATION ====================

    async def create_payment_configuration(
        self,
        configuration_name: str,
        purpose_code: str,
        merchant_category_code: str,
        provider_name: str,
        redirect_url: str,
        jwt_token:str
    ) -> Dict[str, Any]:
        """
        Create Payment Configuration.
        
        Endpoint: POST /payment_configuration

        Args:
            configuration_name: Name of the payment configuration.
            purpose_code: Purpose code (e.g., "00").
            merchant_category_code: Merchant category code (e.g., "0000").
            provider_name: Payment provider name (e.g., "razorpay").
            redirect_url: Redirect URL after payment.

        Returns:
            Dict[str, Any]: A dictionary containing the created configuration
            as returned by the AiSensy API.
        """
        if not configuration_name or not purpose_code or not merchant_category_code or not provider_name or not redirect_url:
            logger.error("Missing required parameters")
            return {
                "success": False,
                "error": "Missing required fields: configuration_name, purpose_code, merchant_category_code, provider_name, redirect_url"
            }

        url = f"{self.BASE_URL}/payment_configuration"
        payload = {
            "configuration_name": configuration_name,
            "purpose_code": purpose_code,
            "merchant_category_code": merchant_category_code,
            "provider_name": provider_name,
            "redirect_url": redirect_url
        }
        logger.debug(f"Creating payment configuration: {configuration_name}")

        try:
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {jwt_token}"
            }

            session = await self._get_session()
            async with session.post(url, json=payload,headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully created payment configuration: {configuration_name}")
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

    # ==================== 25. GENERATE PAYMENT CONFIGURATION OAUTH LINK ====================

    async def generate_payment_configuration_oauth_link(
        self,
        configuration_name: str,
        redirect_url: str,
        jwt_token:str
    ) -> Dict[str, Any]:
        """
        Generate Payment Configuration OAuth Link.
        
        Endpoint: POST /generate_payment_configuration_oauth_link

        Args:
            configuration_name: Name of the payment configuration.
            redirect_url: Redirect URL after OAuth.

        Returns:
            Dict[str, Any]: A dictionary containing the OAuth link
            as returned by the AiSensy API.
        """
        if not configuration_name or not redirect_url:
            logger.error("Missing required parameters")
            return {
                "success": False,
                "error": "Missing required fields: configuration_name and redirect_url"
            }

        url = f"{self.BASE_URL}/generate_payment_configuration_oauth_link"
        payload = {
            "configuration_name": configuration_name,
            "redirect_url": redirect_url
        }
        logger.debug(f"Generating OAuth link for: {configuration_name}")

        try:
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {jwt_token}"
            }


            session = await self._get_session()
            async with session.post(url, json=payload,headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully generated OAuth link for: {configuration_name}")
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