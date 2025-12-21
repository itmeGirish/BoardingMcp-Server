"""
AiSensy Direct API Clients

Client Management:
- Uses shared clients with connection pooling via client managers
- Clients are reused across concurrent requests (no close during active use)
- Call `shutdown_all_direct_api_clients()` during application shutdown for cleanup

Available Clients:
- AiSensyDirectApiGetClient: 19 GET methods (business info, templates, flows, etc.)
- AiSensyDirectApiPostClient: 25 POST methods (send messages, create templates, etc.)
- AiSensyDirectApiDeleteClient: 5 DELETE methods (delete templates, flows, etc.)
- AiSensyDirectApiPatchClient: 4 PATCH methods (update profile, flows, etc.)

Usage:
    from aisensy_direct_api_clients import get_direct_api_get_client

    async with get_direct_api_get_client() as client:
        result = await client.get_business_info()
"""

from .direct_api_client_manager import (
    # Client Managers
    AiSensyDirectApiGetClientManager,
    AiSensyDirectApiPostClientManager,
    AiSensyDirectApiDeleteClientManager,
    AiSensyDirectApiPatchClientManager,
    # Convenience context managers
    get_direct_api_get_client,
    get_direct_api_post_client,
    get_direct_api_delete_client,
    get_direct_api_patch_client,
    # Shutdown function
    shutdown_all_direct_api_clients,
)


__all__ = [
    # Client Managers
    "AiSensyDirectApiGetClientManager",
    "AiSensyDirectApiPostClientManager",
    "AiSensyDirectApiDeleteClientManager",
    "AiSensyDirectApiPatchClientManager",
    # Convenience context managers
    "get_direct_api_get_client",
    "get_direct_api_post_client",
    "get_direct_api_delete_client",
    "get_direct_api_patch_client",
    # Shutdown function
    "shutdown_all_direct_api_clients",
]
