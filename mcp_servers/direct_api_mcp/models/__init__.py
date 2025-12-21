"""
Pydantic models for MCP tool request validation for Direct API.
"""

# GET Request Models
from .direct_api_get_request import (
    TemplateIdRequest,
    UploadSessionIdRequest,
    FlowIdRequest as GetFlowIdRequest,
    PaymentConfigurationNameRequest,
)

# POST Request Models
from .direct_api_post_request import (
    RegenerateJwtBearerTokenRequest,
    WabaAnalyticsRequest,
    MessagingHealthStatusRequest,
    SendMessageRequest,
    SendMarketingLiteMessageRequest,
    MarkMessageAsReadRequest,
    SubmitWhatsappTemplateMessageRequest,
    EditTemplateRequest,
    CompareTemplateRequest,
    UploadMediaRequest,
    RetrieveMediaByIdRequest,
    CreateUploadSessionRequest,
    UploadMediaToSessionRequest,
    CreateCatalogRequest,
    ConnectCatalogRequest,
    CreateProductRequest,
    ShowHideCatalogRequest,
    CreateQrCodeAndShortLinkRequest,
    SetBusinessPublicKeyRequest,
    CreateFlowRequest,
    UpdateFlowJsonRequest,
    FlowIdRequest as PostFlowIdRequest,
    CreatePaymentConfigurationRequest,
    GeneratePaymentConfigurationOAuthLinkRequest,
)

# DELETE Request Models
from .direct_api_delete_request import (
    DeleteWaTemplateByIdRequest,
    DeleteWaTemplateByNameRequest,
    DeleteMediaByIdRequest,
    DeleteFlowRequest,
)

# PATCH Request Models
from .direct_api_patch_request import (
    UpdateBusinessProfilePictureRequest,
    UpdateBusinessProfileDetailsRequest,
    UpdateQrCodeRequest,
    UpdateFlowMetadataRequest,
)

__all__ = [
    # GET
    "TemplateIdRequest",
    "UploadSessionIdRequest",
    "GetFlowIdRequest",
    "PaymentConfigurationNameRequest",
    # POST
    "RegenerateJwtBearerTokenRequest",
    "WabaAnalyticsRequest",
    "MessagingHealthStatusRequest",
    "SendMessageRequest",
    "SendMarketingLiteMessageRequest",
    "MarkMessageAsReadRequest",
    "SubmitWhatsappTemplateMessageRequest",
    "EditTemplateRequest",
    "CompareTemplateRequest",
    "UploadMediaRequest",
    "RetrieveMediaByIdRequest",
    "CreateUploadSessionRequest",
    "UploadMediaToSessionRequest",
    "CreateCatalogRequest",
    "ConnectCatalogRequest",
    "CreateProductRequest",
    "ShowHideCatalogRequest",
    "CreateQrCodeAndShortLinkRequest",
    "SetBusinessPublicKeyRequest",
    "CreateFlowRequest",
    "UpdateFlowJsonRequest",
    "PostFlowIdRequest",
    "CreatePaymentConfigurationRequest",
    "GeneratePaymentConfigurationOAuthLinkRequest",
    # DELETE
    "DeleteWaTemplateByIdRequest",
    "DeleteWaTemplateByNameRequest",
    "DeleteMediaByIdRequest",
    "DeleteFlowRequest",
    # PATCH
    "UpdateBusinessProfilePictureRequest",
    "UpdateBusinessProfileDetailsRequest",
    "UpdateQrCodeRequest",
    "UpdateFlowMetadataRequest",
]