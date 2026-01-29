"""
Pydantic models for MCP tool request validation for Direct API POST requests.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class RegenerateJwtBearerTokenRequest(BaseModel):
    """Model for regenerate JWT bearer token request."""
    
    direct_api: bool = Field(
        default=True,
        description="Whether to use direct API"
    )


class WabaAnalyticsRequest(BaseModel):
    """Model for WABA analytics request."""
    
    fields: str = Field(
        ...,
        description="Analytics fields to fetch",
        examples=["analytics"]
    )
    start: int = Field(
        ...,
        description="Start timestamp (Unix epoch)",
        examples=[1685776770]
    )
    end: int = Field(
        ...,
        description="End timestamp (Unix epoch)",
        examples=[1688368770]
    )
    granularity: str = Field(
        ...,
        description="Data granularity (DAY, MONTH, HOUR)",
        examples=["DAY", "MONTH"]
    )
    country_codes: Optional[List[str]] = Field(
        default=None,
        description="List of country codes to filter",
        examples=[["IN", "US"]]
    )
    
    @field_validator("granularity")
    @classmethod
    def validate_granularity(cls, v: str) -> str:
        """Validate granularity value."""
        valid_values = ["DAY", "MONTH", "HOUR"]
        v = v.upper().strip()
        if v not in valid_values:
            raise ValueError(f"granularity must be one of: {valid_values}")
        return v


class MessagingHealthStatusRequest(BaseModel):
    """Model for messaging health status request."""
    
    node_id: str = Field(
        ...,
        description="The node ID to check health status for",
        min_length=1,
        examples=["node_123"]
    )
    
    @field_validator("node_id")
    @classmethod
    def validate_node_id(cls, v: str) -> str:
        """Validate and sanitize node_id."""
        v = v.strip()
        if not v:
            raise ValueError("node_id cannot be empty or whitespace")
        return v


class SendMessageRequest(BaseModel):
    """Model for send message request. Supports text, image, video, audio, document, template, and interactive types."""

    to: str = Field(
        ...,
        description="Recipient phone number",
        min_length=10,
        examples=["917089379345"]
    )
    message_type: str = Field(
        default="text",
        description="Type of message: text, image, video, audio, document, template, interactive",
        examples=["text", "image", "template", "interactive"]
    )
    text_body: Optional[str] = Field(
        default=None,
        description="The message body text (required for type 'text')",
        examples=["Hello from AiSensy!"]
    )
    media_link: Optional[str] = Field(
        default=None,
        description="URL of the media (required for image, video, audio, document types)",
        examples=["https://example.com/image.png"]
    )
    media_caption: Optional[str] = Field(
        default=None,
        description="Caption for the media (optional, for image, video, document types)"
    )
    media_filename: Optional[str] = Field(
        default=None,
        description="Filename for document type messages"
    )
    template_name: Optional[str] = Field(
        default=None,
        description="Template name (required for type 'template')",
        examples=["sample_shipping_confirmation"]
    )
    template_language_code: Optional[str] = Field(
        default=None,
        description="Template language code (required for type 'template')",
        examples=["en_us"]
    )
    template_language_policy: Optional[str] = Field(
        default="deterministic",
        description="Template language policy (default: 'deterministic')"
    )
    template_components: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Template components list (optional for type 'template')"
    )
    interactive: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Interactive message object (required for type 'interactive'). Contains type, body, footer, action, etc."
    )
    recipient_type: str = Field(
        default="individual",
        description="Type of recipient",
        examples=["individual"]
    )

    @field_validator("to")
    @classmethod
    def validate_to(cls, v: str) -> str:
        """Validate and sanitize phone number."""
        v = v.strip()
        if not v:
            raise ValueError("to cannot be empty or whitespace")
        return v

    @field_validator("text_body")
    @classmethod
    def validate_text_body(cls, v: Optional[str]) -> Optional[str]:
        """Validate and sanitize text_body."""
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("text_body cannot be empty or whitespace")
        return v


class SendMarketingLiteMessageRequest(SendMessageRequest):
    """Model for send marketing lite message request (same as SendMessageRequest)."""
    pass


class MarkMessageAsReadRequest(BaseModel):
    """Model for mark message as read request."""
    
    message_id: str = Field(
        ...,
        description="The message ID to mark as read",
        min_length=1,
        examples=["wamid.HBkMOTE3ODg5Mzc5MzQ1FQIAEhgUM0FENTE1QkQzRkU0RTMyRjQ5MzIA"]
    )
    
    @field_validator("message_id")
    @classmethod
    def validate_message_id(cls, v: str) -> str:
        """Validate and sanitize message_id."""
        v = v.strip()
        if not v:
            raise ValueError("message_id cannot be empty or whitespace")
        return v


class SubmitWhatsappTemplateMessageRequest(BaseModel):
    """Model for submit WhatsApp template message request."""
    
    name: str = Field(
        ...,
        description="Template name",
        min_length=1,
        examples=["my_first_template"]
    )
    category: str = Field(
        ...,
        description="Template category (MARKETING, UTILITY, AUTHENTICATION)",
        examples=["MARKETING", "UTILITY"]
    )
    language: str = Field(
        ...,
        description="Template language",
        examples=["en_US", "hi"]
    )
    components: List[Dict[str, Any]] = Field(
        ...,
        description="List of template components (HEADER, BODY, FOOTER, BUTTONS)"
    )
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and sanitize template name."""
        v = v.strip()
        if not v:
            raise ValueError("name cannot be empty or whitespace")
        return v
    
    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate category value."""
        valid_values = ["MARKETING", "UTILITY", "AUTHENTICATION"]
        v = v.upper().strip()
        if v not in valid_values:
            raise ValueError(f"category must be one of: {valid_values}")
        return v


class EditTemplateRequest(BaseModel):
    """Model for edit template request."""
    
    template_id: str = Field(
        ...,
        description="The template ID to edit",
        min_length=1,
        examples=["156167230836488"]
    )
    category: str = Field(
        ...,
        description="Template category (MARKETING, UTILITY, AUTHENTICATION)",
        examples=["MARKETING", "UTILITY"]
    )
    components: List[Dict[str, Any]] = Field(
        ...,
        description="List of template components (HEADER, BODY, FOOTER, BUTTONS)"
    )
    
    @field_validator("template_id")
    @classmethod
    def validate_template_id(cls, v: str) -> str:
        """Validate and sanitize template_id."""
        v = v.strip()
        if not v:
            raise ValueError("template_id cannot be empty or whitespace")
        return v


class CompareTemplateRequest(BaseModel):
    """Model for compare template request."""
    
    template_id: str = Field(
        ...,
        description="The primary template ID for comparison",
        min_length=1,
        examples=["156167230836488"]
    )
    template_ids: List[int] = Field(
        ...,
        description="List of template IDs to compare",
        examples=[[156167230836488]]
    )
    start: int = Field(
        ...,
        description="Start timestamp (Unix epoch)",
        examples=[1683971511]
    )
    end: int = Field(
        ...,
        description="End timestamp (Unix epoch)",
        examples=[1691747511]
    )
    
    @field_validator("template_id")
    @classmethod
    def validate_template_id(cls, v: str) -> str:
        """Validate and sanitize template_id."""
        v = v.strip()
        if not v:
            raise ValueError("template_id cannot be empty or whitespace")
        return v


class UploadMediaRequest(BaseModel):
    """Model for upload media request."""
    
    file_path: str = Field(
        ...,
        description="Path to the file to upload",
        min_length=1,
        examples=["/path/to/image.jpg"]
    )
    
    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, v: str) -> str:
        """Validate and sanitize file_path."""
        v = v.strip()
        if not v:
            raise ValueError("file_path cannot be empty or whitespace")
        return v


class RetrieveMediaByIdRequest(BaseModel):
    """Model for retrieve media by ID request."""
    
    media_id: str = Field(
        ...,
        description="The media ID to fetch",
        min_length=1,
        examples=["media_abc123"]
    )
    
    @field_validator("media_id")
    @classmethod
    def validate_media_id(cls, v: str) -> str:
        """Validate and sanitize media_id."""
        v = v.strip()
        if not v:
            raise ValueError("media_id cannot be empty or whitespace")
        return v


class CreateUploadSessionRequest(BaseModel):
    """Model for create upload session request."""
    
    file_name: str = Field(
        ...,
        description="Name of the file to upload",
        min_length=1,
        examples=["test_image.jpg"]
    )
    file_length: str = Field(
        ...,
        description="Size of the file in bytes",
        examples=["69728"]
    )
    file_type: str = Field(
        ...,
        description="MIME type of the file",
        examples=["image/jpg", "video/mp4"]
    )
    
    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, v: str) -> str:
        """Validate and sanitize file_name."""
        v = v.strip()
        if not v:
            raise ValueError("file_name cannot be empty or whitespace")
        return v


class UploadMediaToSessionRequest(BaseModel):
    """Model for upload media to session request."""
    
    upload_session_id: str = Field(
        ...,
        description="The upload session ID",
        min_length=1,
        examples=["session_abc123"]
    )
    file_path: str = Field(
        ...,
        description="Path to the file to upload",
        min_length=1,
        examples=["/path/to/image.jpg"]
    )
    file_offset: int = Field(
        default=0,
        description="Byte offset for resumable uploads",
        examples=[0]
    )
    
    @field_validator("upload_session_id", "file_path")
    @classmethod
    def validate_required_strings(cls, v: str) -> str:
        """Validate and sanitize required string fields."""
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or whitespace")
        return v


class CreateCatalogRequest(BaseModel):
    """Model for create catalog request."""
    
    name: str = Field(
        ...,
        description="Catalog name",
        min_length=1,
        examples=["my-new-catalogue"]
    )
    vertical: str = Field(
        default="commerce",
        description="Catalog vertical",
        examples=["commerce"]
    )
    product_count: int = Field(
        default=0,
        description="Number of products",
        examples=[10]
    )
    feed_count: int = Field(
        default=1,
        description="Number of feeds",
        examples=[1]
    )
    default_image_url: Optional[str] = Field(
        default=None,
        description="Default image URL"
    )
    fallback_image_url: Optional[List[str]] = Field(
        default=None,
        description="List of fallback image URLs"
    )
    is_catalog_segment: bool = Field(
        default=False,
        description="Whether catalog is a segment"
    )
    da_display_settings: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Display settings for dynamic ads"
    )
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and sanitize catalog name."""
        v = v.strip()
        if not v:
            raise ValueError("name cannot be empty or whitespace")
        return v


class ConnectCatalogRequest(BaseModel):
    """Model for connect catalog request."""
    
    catalog_id: str = Field(
        ...,
        description="The catalog ID to connect",
        min_length=1,
        examples=["570811508315768"]
    )
    
    @field_validator("catalog_id")
    @classmethod
    def validate_catalog_id(cls, v: str) -> str:
        """Validate and sanitize catalog_id."""
        v = v.strip()
        if not v:
            raise ValueError("catalog_id cannot be empty or whitespace")
        return v


class CreateProductRequest(BaseModel):
    """Model for create product request."""
    
    catalog_id: str = Field(
        ...,
        description="The catalog ID to add product to",
        min_length=1,
        examples=["1800221970545934"]
    )
    name: str = Field(
        ...,
        description="Product name",
        min_length=1,
        examples=["AirMax"]
    )
    category: str = Field(
        ...,
        description="Product category",
        min_length=1,
        examples=["Sneakers"]
    )
    currency: str = Field(
        ...,
        description="Currency code",
        examples=["INR", "USD"]
    )
    image_url: str = Field(
        ...,
        description="Product image URL",
        min_length=1
    )
    price: str = Field(
        ...,
        description="Product price",
        examples=["15000"]
    )
    retailer_id: str = Field(
        ...,
        description="Retailer ID",
        min_length=1,
        examples=["1001511"]
    )
    description: Optional[str] = Field(
        default=None,
        description="Product description"
    )
    url: Optional[str] = Field(
        default=None,
        description="Product URL"
    )
    brand: Optional[str] = Field(
        default=None,
        description="Product brand"
    )
    sale_price: Optional[str] = Field(
        default=None,
        description="Sale price"
    )
    sale_price_start_date: Optional[str] = Field(
        default=None,
        description="Sale start date"
    )
    sale_price_end_date: Optional[str] = Field(
        default=None,
        description="Sale end date"
    )


class ShowHideCatalogRequest(BaseModel):
    """Model for show/hide catalog request."""
    
    enable_catalog: bool = Field(
        ...,
        description="Whether to enable catalog"
    )
    enable_cart: bool = Field(
        ...,
        description="Whether to enable cart"
    )


class CreateQrCodeAndShortLinkRequest(BaseModel):
    """Model for create QR code and short link request."""
    
    prefilled_message: str = Field(
        ...,
        description="The prefilled message for the QR code",
        min_length=1,
        examples=["Cyber Monday"]
    )
    generate_qr_image: str = Field(
        default="SVG",
        description="QR image format (SVG, PNG)",
        examples=["SVG", "PNG"]
    )
    
    @field_validator("prefilled_message")
    @classmethod
    def validate_prefilled_message(cls, v: str) -> str:
        """Validate and sanitize prefilled_message."""
        v = v.strip()
        if not v:
            raise ValueError("prefilled_message cannot be empty or whitespace")
        return v


class SetBusinessPublicKeyRequest(BaseModel):
    """Model for set business public key request."""
    
    business_public_key: str = Field(
        ...,
        description="The business public key (PEM format)",
        min_length=1
    )
    
    @field_validator("business_public_key")
    @classmethod
    def validate_business_public_key(cls, v: str) -> str:
        """Validate and sanitize business_public_key."""
        v = v.strip()
        if not v:
            raise ValueError("business_public_key cannot be empty or whitespace")
        return v


class CreateFlowRequest(BaseModel):
    """Model for create flow request."""
    
    name: str = Field(
        ...,
        description="Flow name",
        min_length=1,
        examples=["My first flow"]
    )
    categories: List[str] = Field(
        ...,
        description="List of flow categories",
        examples=[["APPOINTMENT_BOOKING"]]
    )
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and sanitize flow name."""
        v = v.strip()
        if not v:
            raise ValueError("name cannot be empty or whitespace")
        return v


class UpdateFlowJsonRequest(BaseModel):
    """Model for update flow JSON request."""
    
    flow_id: str = Field(
        ...,
        description="The flow ID to upload assets to",
        min_length=1,
        examples=["flow_abc123"]
    )
    file_path: str = Field(
        ...,
        description="Path to the file to upload",
        min_length=1,
        examples=["/path/to/asset.json"]
    )
    
    @field_validator("flow_id", "file_path")
    @classmethod
    def validate_required_strings(cls, v: str) -> str:
        """Validate and sanitize required string fields."""
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or whitespace")
        return v


class FlowIdRequest(BaseModel):
    """Model for flow ID based requests (publish/deprecate)."""
    
    flow_id: str = Field(
        ...,
        description="The flow ID",
        min_length=1,
        examples=["flow_abc123"]
    )
    
    @field_validator("flow_id")
    @classmethod
    def validate_flow_id(cls, v: str) -> str:
        """Validate and sanitize flow_id."""
        v = v.strip()
        if not v:
            raise ValueError("flow_id cannot be empty or whitespace")
        return v


class CreatePaymentConfigurationRequest(BaseModel):
    """Model for create payment configuration request."""
    
    configuration_name: str = Field(
        ...,
        description="Name of the payment configuration",
        min_length=1,
        examples=["test-payment-configuration"]
    )
    purpose_code: str = Field(
        ...,
        description="Purpose code",
        examples=["00"]
    )
    merchant_category_code: str = Field(
        ...,
        description="Merchant category code",
        examples=["0000"]
    )
    provider_name: str = Field(
        ...,
        description="Payment provider name",
        examples=["razorpay"]
    )
    redirect_url: str = Field(
        ...,
        description="Redirect URL after payment",
        min_length=1,
        examples=["https://test-redirect-url.com"]
    )
    
    @field_validator("configuration_name", "redirect_url")
    @classmethod
    def validate_required_strings(cls, v: str) -> str:
        """Validate and sanitize required string fields."""
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or whitespace")
        return v


class GeneratePaymentConfigurationOAuthLinkRequest(BaseModel):
    """Model for generate payment configuration OAuth link request."""
    
    configuration_name: str = Field(
        ...,
        description="Name of the payment configuration",
        min_length=1,
        examples=["test-payment-configuration"]
    )
    redirect_url: str = Field(
        ...,
        description="Redirect URL after OAuth",
        min_length=1,
        examples=["https://test-redirect-url.com"]
    )
    
    @field_validator("configuration_name", "redirect_url")
    @classmethod
    def validate_required_strings(cls, v: str) -> str:
        """Validate and sanitize required string fields."""
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or whitespace")
        return v