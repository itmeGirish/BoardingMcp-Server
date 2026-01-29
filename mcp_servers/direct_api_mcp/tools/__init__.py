from fastmcp import FastMCP

mcp = FastMCP(
    name="Directapi Server",
    instructions="""...""",
    version="0.0.1"
)

# Catalog tools
from .catalog import (
    get_catalog,
    get_products,
    connect_catalog,
    create_catalog,
    create_product,
    disconnect_catalog,
)

# Commerce tools
from .commerce import get_commerce_settings, show_hide_catalog

# Direct API tools
from .direct_api import (
    get_fb_verification_status,
    get_business_info,
    regenerate_jwt_bearer_token,
    get_waba_analytics,
    get_messaging_health_status,
)

# Flows tools
from .flows import (
    get_flows,
    get_flow_by_id,
    get_flow_assets,
    create_flow,
    update_flow_json,
    publish_flow,
    deprecate_flow,
    delete_flow,
    update_flow_metadata,
)

# Media tools
from .media import (
    get_media_upload_session,
    upload_media,
    retrieve_media_by_id,
    create_upload_session,
    upload_media_to_session,
    delete_media_by_id,
)

# Messages tools
from .messages import send_message, send_marketing_lite_message, mark_message_as_read

from .templates import (compare_template,edit_template,submit_whatsapp_template_message,
                                  get_templates,get_template_by_id,
                                  delete_wa_template_by_id,delete_wa_template_by_id)

# Phone number tools
from .phone_number import (
    get_all_phone_numbers,
    get_display_name_status,
    get_single_phone_number,
)

# Profile tools
from .profile import (
    get_profile,
    update_business_profile_picture,
    update_business_profile_details,
)

# QR codes and short links tools
from .qr_codes_and_short_links import (
    get_qr_codes,
    create_qr_code_and_short_link,
    update_qr_code,
)

# WhatsApp Business Encryption tools
from .whatsp_business_encryption import (
    get_whatsapp_business_encryption,
    set_business_public_key,
)

# WhatsApp Payments tools
from .whatsp_payments import (
    get_payment_configurations,
    get_payment_configuration_by_name,
    generate_payment_configuration_oauth_link,
    create_payment_configuration,
)


__all__ = [
    "mcp",
    # Catalog
    "get_catalog",
    "get_products",
    "connect_catalog",
    "create_catalog",
    "create_product",
    "disconnect_catalog",
    # Commerce
    "get_commerce_settings",
    "show_hide_catalog",
    # Direct API
    "get_fb_verification_status",
    "get_business_info",
    "regenerate_jwt_bearer_token",
    "get_waba_analytics",
    "get_messaging_health_status",
    # Flows
    "get_flows",
    "get_flow_by_id",
    "get_flow_assets",
    "create_flow",
    "update_flow_json",
    "publish_flow",
    "deprecate_flow",
    "delete_flow",
    "update_flow_metadata",
    # Media
    "get_media_upload_session",
    "upload_media",
    "retrieve_media_by_id",
    "create_upload_session",
    "upload_media_to_session",
    "delete_media_by_id",
    # Messages
    "send_message",
    "send_marketing_lite_message",
    "mark_message_as_read",
    # Phone number
    "get_all_phone_numbers",
    "get_display_name_status",
    "get_single_phone_number",
    # Profile
    "get_profile",
    "update_business_profile_picture",
    "update_business_profile_details",
    # QR codes
    "get_qr_codes",
    "create_qr_code_and_short_link",
    "update_qr_code",
    # Encryption
    "get_whatsapp_business_encryption",
    "set_business_public_key",
    # Payments
    "get_payment_configurations",
    "get_payment_configuration_by_name",
    "generate_payment_configuration_oauth_link",
    "create_payment_configuration",
    
    #templates
    "compare_template",
    "edit_template",
    "submit_whatsapp_template_message",
    "get_templates",
    "get_template_by_id",
    "delete_wa_template_by_id",
    "delete_wa_template_by_id"
]