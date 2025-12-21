from fastmcp import FastMCP

mcp = FastMCP(
    name="OnboardingAssistant",
    instructions="""...""",
    version="0.0.1"
)


from .get_tools import get_business_profile_by_id,get_all_business_profiles,get_kyc_submission_status,get_business_verification_status,get_partner_details,get_wcc_usage_analytics,get_billing_records,get_all_business_projects,get_project_by_id
from .post_tools import create_business_profile,create_project,generate_embedded_signup_url,submit_waba_app_id,start_migration,request_otp_for_verification,verify_otp,generate_embedded_fb_catalog_url,generate_ctwa_ads_dashboard_url
from .patch_tools import update_business_details