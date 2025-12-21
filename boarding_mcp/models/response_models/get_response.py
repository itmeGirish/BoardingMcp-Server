from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict


# ============================================================
# 1. get_business_profile_by_id
# ============================================================

class BusinessProfile(BaseModel):
    """Response model for get_business_profile_by_id endpoint."""

    id: str 
    active: bool
    display_name: str
    project_ids: List[str]
    user_name: str
    business_id: str
    email: str
    created_at: int
    updated_at: int
    company: str
    contact: str
    currency: str
    timezone: str
    partner_id: str
    type: str
    company_size: int = Field(alias="companySize")
    password: bool
    
    class ConfigDict:
        populate_by_name = True


# ============================================================
# 2. get_all_business_profiles
# ============================================================

class BusinessProfileItem(BaseModel):
    """Individual business profile in the list."""
    
    id: str
    active: bool
    display_name: str
    project_ids: List[str]
    user_name: str
    business_id: str
    email: str
    created_at: int
    updated_at: int
    company: str
    contact: str
    currency: str
    timezone: str
    partner_id: str
    type: str
    created_on: Optional[str] = Field(default=None, alias="createdOn")
    company_size: int = Field(alias="companySize")
    password: bool
    
    class ConfigDict:
        populate_by_name = True


class AllBusinessProfilesResponse(BaseModel):
    """Response model for get_all_business_profiles endpoint."""
    
    profiles: List[BusinessProfileItem]


# ============================================================
# 3. get_kyc_submission_status
# ============================================================

class KycSubmissionStatusData(BaseModel):
    """Inner data for KYC submission status."""
    
    data: List[Any]


class KycSubmissionStatusResponse(BaseModel):
    """Response model for get_kyc_submission_status endpoint."""
    
    success: bool
    data: KycSubmissionStatusData


# ============================================================
# 4. get_business_verification_status
# ============================================================

class BusinessVerificationStatusData(BaseModel):
    """Data for business verification status."""
    
    verification_status: str
    id: str


class BusinessVerificationStatusResponse(BaseModel):
    """Response model for get_business_verification_status endpoint."""
    
    success: bool
    data: BusinessVerificationStatusData


# ============================================================
# 5. get_partner_details
# ============================================================

class PartnerDetails(BaseModel):
    """Response model for get_partner_details endpoint."""
    
    id: str
    name: str
    display_name: str
    central_balance: float = Field(alias="centralBalance")
    currency: str
    webhook_url: str
    created_at: int
    updated_at: int

    class ConfigDict:
        populate_by_name = True


# ============================================================
# 6. get_wcc_usage_analytics
# ============================================================

class CountryWiseMetric(BaseModel):
    """Country-wise amount and count."""
    
    amount: float
    count: int


class CentralBalanceMetrics(BaseModel):
    """Central balance metrics with country-wise breakdown."""
    
    count: int
    credit_usage: float = Field(alias="creditUsage")
    credit_usage_country_wise: Dict[str, CountryWiseMetric] = Field(
        default_factory=dict, 
        alias="creditUsageCountryWise"
    )
    
    class ConfigDict:
        populate_by_name = True


class WccAnalyticsItem(BaseModel):
    """Individual WCC analytics record for a day."""
    
    # MongoDB fields
    id: Optional[str] = Field(default=None, alias="_id")
    v: Optional[int] = Field(default=None, alias="__v")
    
    # Core identifiers
    assistant_id: Optional[str] = Field(default=None, alias="assistantId")
    client_id: Optional[str] = Field(default=None, alias="clientId")
    partner_id: Optional[str] = Field(default=None, alias="partnerId")
    campaign_id: Optional[str] = Field(default=None, alias="campaignId")
    affiliate_id: Optional[str] = Field(default=None, alias="affiliateId")
    
    # Date fields
    day_date: str = Field(alias="dayDate")
    created_at: Optional[str] = Field(default=None, alias="createdAt")
    updated_at: Optional[str] = Field(default=None, alias="updatedAt")
    timezone: Optional[str] = None
    
    # Chat counts
    total_chat_count: Optional[int] = Field(default=None, alias="totalChatCount")
    sent_chat_count: Optional[int] = Field(default=None, alias="sentChatCount")
    delivered_chat_count: Optional[int] = Field(default=None, alias="deliveredChatCount")
    read_chat_count: Optional[int] = Field(default=None, alias="readChatCount")
    failed_chat_count: Optional[int] = Field(default=None, alias="failedChatCount")
    enqueued_chat_count: Optional[int] = Field(default=None, alias="enqueuedChatCount")
    
    # Central balance usage
    central_balance_used_count: Optional[float] = Field(default=None, alias="centralBalanceUsedCount")
    central_balance_used_country_wise: Optional[Dict[str, CountryWiseMetric]] = Field(
        default=None, 
        alias="centralBalanceUsedCountryWise"
    )
    central_balance_messages_count: Optional[int] = Field(default=None, alias="centralBalanceMessagesCount")
    
    # Template credit usage
    template_credit_used_count: Optional[float] = Field(default=None, alias="templateCreditUsedCount")
    template_credit_used_country_wise: Optional[Dict[str, CountryWiseMetric]] = Field(
        default=None, 
        alias="templateCreditUsedCountryWise"
    )
    template_messages_count: Optional[int] = Field(default=None, alias="templateMessagesCount")
    free_tier_count: Optional[int] = Field(default=None, alias="freeTierCount")
    
    # Central Balance Metrics by category
    sc_central_balance_metrics: Optional[CentralBalanceMetrics] = Field(
        default=None, 
        alias="scCentralBalanceMetrics"
    )
    uc_central_balance_metrics: Optional[CentralBalanceMetrics] = Field(
        default=None, 
        alias="ucCentralBalanceMetrics"
    )
    uic_central_balance_metrics: Optional[CentralBalanceMetrics] = Field(
        default=None, 
        alias="uicCentralBalanceMetrics"
    )
    bic_central_balance_metrics: Optional[CentralBalanceMetrics] = Field(
        default=None, 
        alias="bicCentralBalanceMetrics"
    )
    ac_central_balance_metrics: Optional[CentralBalanceMetrics] = Field(
        default=None, 
        alias="acCentralBalanceMetrics"
    )
    mc_central_balance_metrics: Optional[CentralBalanceMetrics] = Field(
        default=None, 
        alias="mcCentralBalanceMetrics"
    )
    
    # Template Credit Metrics by category
    sc_template_credit_metrics: Optional[CentralBalanceMetrics] = Field(
        default=None, 
        alias="scTemplateCreditMetrics"
    )
    uc_template_credit_metrics: Optional[CentralBalanceMetrics] = Field(
        default=None, 
        alias="ucTemplateCreditMetrics"
    )
    uic_template_credit_metrics: Optional[CentralBalanceMetrics] = Field(
        default=None, 
        alias="uicTemplateCreditMetrics"
    )
    bic_template_credit_metrics: Optional[CentralBalanceMetrics] = Field(
        default=None, 
        alias="bicTemplateCreditMetrics"
    )
    ac_template_credit_metrics: Optional[CentralBalanceMetrics] = Field(
        default=None, 
        alias="acTemplateCreditMetrics"
    )
    mc_template_credit_metrics: Optional[CentralBalanceMetrics] = Field(
        default=None, 
        alias="mcTemplateCreditMetrics"
    )

    class ConfigDict:
        populate_by_name = True


class WccAnalyticsData(BaseModel):
    """Data wrapper for WCC analytics."""
    
    wcc_analytics: List[WccAnalyticsItem] = Field(alias="wccAnalytics")
    
    class ConfigDict:
        populate_by_name = True


class WccUsageAnalyticsResponse(BaseModel):
    """Response model for get_wcc_usage_analytics endpoint."""
    
    success: bool
    data: WccAnalyticsData


# ============================================================
# 7. get_billing_records
# ============================================================

class BillingRecordItem(BaseModel):
    """Individual billing record."""
    
    id: str = Field(alias="_id")
    v: Optional[int] = Field(default=None, alias="__v")
    partner_id: str = Field(alias="partnerId")
    action: str  # e.g., "SUBTRACT", "ADD"
    amount: int
    prev_central_balance: int = Field(alias="prevCentralBalance")
    reason_code: str = Field(alias="reasonCode")  # e.g., "PLAN_RENEWED"
    message: str
    assistant_id: str = Field(alias="assistantId")
    client_id: str = Field(alias="clientId")
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")

    class ConfigDict:
        populate_by_name = True


class BillingRecordsData(BaseModel):
    """Data wrapper for billing records."""
    
    data: List[BillingRecordItem]


class BillingRecordsResponse(BaseModel):
    """Response model for get_billing_records endpoint."""
    
    success: bool
    data: BillingRecordsData


# ============================================================
# 8 & 9. get_all_business_projects / get_project_by_id
# (Both return same structure)
# ============================================================

class WhatsAppBusinessProfile(BaseModel):
    """WhatsApp business profile details."""
    
    address: Optional[str] = None
    description: Optional[str] = None
    email: Optional[str] = None
    websites: Optional[List[str]] = None
    vertical: Optional[str] = None


class ProjectDetails(BaseModel):
    """Project details model."""
    
    type: str
    id: str
    name: str
    business_id: str
    partner_id: str
    plan_activated_on: Optional[int] = None
    status: str
    sandbox: bool
    active_plan: Optional[str] = None
    created_at: int
    updated_at: int
    plan_renewal_on: Optional[int] = None
    scheduled_subscription_changes: Optional[Any] = None
    mau_quota: Optional[int] = None
    mau_usage: Optional[int] = None
    credit: Optional[int] = None
    wa_number: Optional[str] = None
    wa_messaging_tier: Optional[str] = None
    wa_display_name_status: Optional[str] = None
    fb_business_manager_status: Optional[str] = None
    wa_display_name: Optional[str] = None
    wa_quality_rating: Optional[str] = None
    wa_about: Optional[str] = None
    wa_display_image: Optional[str] = None
    wa_business_profile: Optional[WhatsAppBusinessProfile] = None
    billing_currency: Optional[str] = None
    timezone: Optional[str] = None
    subscription_started_on: Optional[int] = None
    is_whatsapp_verified: Optional[bool] = None
    subscription_status: Optional[str] = None
    daily_template_limit: Optional[int] = None
    waba_app_status: Optional[str] = None


class ProjectResponse(BaseModel):
    """Response model for both get_all_business_projects and get_project_by_id endpoints."""
    
    success: bool
    data: ProjectDetails





#============================================================
# 10. get_project_by_id (Old Model - To be Deprecated)

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from enum import Enum


class QualityRating(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"


class DisplayNameStatus(str, Enum):
    APPROVED = "APPROVED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"


class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class BusinessVertical(str, Enum):
    PROF_SERVICES = "PROF_SERVICES"
    RETAIL = "RETAIL"
    EDUCATION = "EDUCATION"
    HEALTH = "HEALTH"
    FINANCIAL = "FINANCIAL"
    OTHER = "OTHER"


class WABusinessProfile(BaseModel):
    address: Optional[str] = None
    description: Optional[str] = None
    email: Optional[str] = None
    websites: Optional[list[str]] = None
    vertical: Optional[str] = None


class ProjectData(BaseModel):
    type: str
    id: str
    name: str
    business_id: str
    partner_id: str
    plan_activated_on: int
    status: str
    sandbox: bool
    active_plan: str
    created_at: int
    updated_at: int
    plan_renewal_on: int
    scheduled_subscription_changes: Optional[dict] = None
    mau_quota: int
    mau_usage: int
    credit: int
    wa_number: str
    wa_messaging_tier: str
    wa_display_name_status: str
    fb_business_manager_status: str
    wa_display_name: str
    wa_quality_rating: str
    wa_about: str
    wa_display_image: Optional[str] = None
    wa_business_profile: WABusinessProfile
    billing_currency: str
    timezone: str
    subscription_started_on: int
    is_whatsapp_verified: bool
    subscription_status: str
    daily_template_limit: int
    waba_app_status: Optional[str] = None


class ProjectIDResponse(BaseModel):
    success: bool
    data: ProjectData