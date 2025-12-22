"""
This is for the pydantic models for get_request, post_request, patch_request
"""
from .request_models import (ProjectIdRequest, BusinessProjectsRequest,
                            CreateBusinessProfileRequest,
                            CreateProjectRequest,
                            EmbeddedSignupUrlRequest,
                            SubmitWabaAppIdRequest,
                            StartMigrationRequest,
                            RequestOtpRequest,
                            VerifyOtpRequest,
                            BusinessAssistantRequest,
                            CtwaAdsDashboardRequest,
                            UpdateBusinessDetailsRequest)

from .response_models import (BusinessProfile,
                           AllBusinessProfilesResponse,
                           KycSubmissionStatusResponse,
                           BusinessVerificationStatusResponse,
                           PartnerDetails,
                           WccUsageAnalyticsResponse,
                           BillingRecordsResponse,
                           ProjectResponse,
                           ProjectIDResponse,
                           BusinessCreationResponse,
                           BusinessCreationWithUserResponse,
                           BusinessCreationWithUserResponse,
                           ProjectAPIResponse,
                           ProjectResponse)


__all__ = [
    "ProjectIdRequest",
    "BusinessProjectsRequest",
    "CreateBusinessProfileRequest",
    "CreateProjectRequest",
    "EmbeddedSignupUrlRequest",
    "SubmitWabaAppIdRequest",
    "StartMigrationRequest",
    "RequestOtpRequest",
    "VerifyOtpRequest",
    "BusinessAssistantRequest",
    "CtwaAdsDashboardRequest",
    "UpdateBusinessDetailsRequest",
    "BusinessProfile",
    "AllBusinessProfilesResponse",
    "KycSubmissionStatusResponse",
    "BusinessVerificationStatusResponse",
    "PartnerDetails",
    "WccUsageAnalyticsResponse",
    "BillingRecordsResponse",
    "ProjectIDResponse",
    "BusinessCreationResponse",
    "BusinessCreationWithUserResponse",
    "BusinessCreationWithUserResponse",
    "ProjectResponse"
]