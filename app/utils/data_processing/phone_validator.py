"""Phone number validation and E.164 normalization using phonenumbers library."""
import phonenumbers
from phonenumbers import PhoneNumberType
from app.config import logger


# Mobile-compatible number types
MOBILE_TYPES = {
    PhoneNumberType.MOBILE,
    PhoneNumberType.FIXED_LINE_OR_MOBILE,
}


def validate_phone(phone: str, default_country: str = "IN") -> tuple:
    """
    Validate a phone number and return E.164 format.

    Handles:
    - Local: 9876543210
    - National: 09876543210
    - International: +919876543210

    Args:
        phone: Raw phone number string
        default_country: ISO 2-letter country code for numbers without country code

    Returns:
        tuple: (is_valid, e164_number, country_code)
            - is_valid: True if number is a valid mobile number
            - e164_number: E.164 formatted number (e.g., "+919876543210") or original if invalid
            - country_code: ISO country code (e.g., "IN") or "" if invalid
    """
    raw = str(phone).strip()
    if not raw:
        return (False, raw, "")

    try:
        parsed = phonenumbers.parse(raw, default_country)

        if not phonenumbers.is_valid_number(parsed):
            logger.debug(f"Invalid phone number: {raw}")
            return (False, raw, "")

        # Check if it's a mobile number (exclude landlines for WhatsApp)
        number_type = phonenumbers.number_type(parsed)
        if number_type not in MOBILE_TYPES:
            logger.debug(f"Non-mobile number type ({number_type}): {raw}")
            return (False, raw, "")

        e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        region = phonenumbers.region_code_for_number(parsed) or ""

        return (True, e164, region)

    except phonenumbers.NumberParseException as e:
        logger.debug(f"Phone parse error for '{raw}': {e}")
        return (False, raw, "")


def normalize_phone(phone: str, default_country: str = "IN") -> str:
    """
    Normalize a phone number to E.164 format.

    Returns E.164 formatted number or the original string if parsing fails.

    Args:
        phone: Raw phone number string
        default_country: ISO 2-letter country code for numbers without country code

    Returns:
        str: E.164 formatted number or original if parsing fails
    """
    raw = str(phone).strip()
    if not raw:
        return raw

    try:
        parsed = phonenumbers.parse(raw, default_country)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        return raw
    except phonenumbers.NumberParseException:
        return raw
