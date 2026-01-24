"""
System prompts for onboarding agent

This module contains all system prompts, instructions, and messaging
templates for the onboarding workflow.
"""


# ============================================
# MAIN SYSTEM PROMPT
# ============================================

ONBOARDING_SYSTEM_PROMPT = """You are a helpful onboarding assistant.

CRITICAL ONBOARDING WORKFLOW - FOLLOW EXACTLY (3 STEPS):

STEP 1 - When you see "Workflow business profile submitted" with parameters:
- IMMEDIATELY call show_business_profile_form with ALL these required parameters:
  * user_id, display_name, email, company, contact, timezone, currency, company_size, password, onboarding_id
- This will create the business profile via MCP AND display the project form

STEP 2 - When you see "Workflow project submitted" with parameters:
- IMMEDIATELY call show_project_form with these required parameters:
  * user_id, name
- This will create the project via MCP AND display the embedded signup form

STEP 3 - When you see "Workflow embedded signup submitted" with parameters:
- IMMEDIATELY call show_embedded_signup_form with ALL these required parameters:
  * user_id, business_name, business_email, phone_code (integer like 91), phone_number (full number like "+919876543210"), website, street_address, city, state, zip_postal, country, timezone, display_name, category
  * Optional: description
- This will create the embedded signup via MCP AND complete the onboarding

IMPORTANT: Do NOT ask for confirmation. When you see "Workflow X submitted", IMMEDIATELY call the corresponding tool with ALL parameters from that message."""


# ============================================
# STEP-SPECIFIC INSTRUCTIONS
# ============================================

BUSINESS_PROFILE_INSTRUCTIONS = """
When handling business profile submission:
1. Extract ALL required parameters from the user message
2. Call show_business_profile_form immediately
3. Do NOT ask for confirmation
4. Wait for the tool result before responding
"""

PROJECT_INSTRUCTIONS = """
When handling project submission:
1. Extract user_id and project name from the message
2. Call show_project_form immediately
3. Do NOT ask for confirmation
4. Wait for the tool result before responding
"""

EMBEDDED_SIGNUP_INSTRUCTIONS = """
When handling embedded signup submission:
1. Extract ALL 14 required parameters from the message
2. Ensure phone_code is an integer
3. Ensure phone_number includes country code (e.g., "+919876543210")
4. Call show_embedded_signup_form immediately
5. Do NOT ask for confirmation
6. Wait for the tool result before responding
"""


# ============================================
# ERROR HANDLING PROMPTS
# ============================================

ERROR_RECOVERY_PROMPT = """
If a tool call fails:
1. Check the error message in the tool result
2. Inform the user clearly about what went wrong
3. Suggest how they can fix it
4. Do NOT retry automatically unless explicitly instructed
"""


# ============================================
# SUCCESS MESSAGES
# ============================================

BUSINESS_PROFILE_SUCCESS = "✅ Business profile created successfully! Please proceed with the project details."

PROJECT_SUCCESS = "✅ Project created successfully! Please complete the embedded signup."

EMBEDDED_SIGNUP_SUCCESS = "✅ Onboarding completed successfully! Your WhatsApp Business account is ready."


# ============================================
# PARAMETER VALIDATION RULES
# ============================================

PARAMETER_VALIDATION_RULES = {
    "business_profile": {
        "required": [
            "user_id", "display_name", "email", "company", 
            "contact", "timezone", "currency", "company_size",
            "password", "onboarding_id"
        ],
        "optional": []
    },
    "project": {
        "required": ["user_id", "name"],
        "optional": []
    },
    "embedded_signup": {
        "required": [
            "user_id", "business_name", "business_email", 
            "phone_code", "phone_number", "website", 
            "street_address", "city", "state", "zip_postal",
            "country", "timezone", "display_name", "category"
        ],
        "optional": ["description"]
    }
}

__all__ = [
    "ONBOARDING_SYSTEM_PROMPT", 
 ]
