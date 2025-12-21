# This is steps for Onboarding it is mcp server

# Client Onboarding

User onboarding primarily includes
1.Creating Business for the Client
2.Creating a Project for the Client
3.Procuring WABA on the project
4.Generate JWT Token
5.Start using Direct APIs

# Onboarding Steps
STEP 1:
Creating Business for the Client
# This creates business profile to busiess
tool: tool_create_business_profile:
Note:For direct API users, make sure to save email & password as this will be needed later

STEP 2:
Creating Project for Business
# This is create project for Business that have been created
tool:tool_create_project
Note:In response you'll receive project detail, do save all details for future use

Step 3:
Procuring WABA on the project
# This is create procuring waba on the project with business ID (from step 1) and  Project Id (from step 2)
tool:tool_generate_embedded_signup_url
Note : 
You can redirect to this URL to complete embedded Signup for WABA procurement



