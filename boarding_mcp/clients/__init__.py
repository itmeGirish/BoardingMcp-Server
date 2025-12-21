"""
This is for import of base clients

Client Management:
- Uses shared clients with connection pooling via AiSensyGetClientManager, AiSensyPostClientManager, and AiSensyPatchClientManager
- Clients are reused across concurrent requests (no close during active use)
- Call `shutdown_all_clients()` during application shutdown for cleanup
"""

from .client_manager import (
    AiSensyGetClientManager,
    AiSensyPostClientManager,
    AiSensyPatchClientManager,
    get_aisensy_get_client,
    get_aisensy_post_client,
    get_aisensy_patch_client,
    get_aisensy_client,  # Backward compatibility alias
    shutdown_all_clients
)


__all__ = ["AiSensyGetClientManager","AiSensyPostClientManager","AiSensyPatchClientManager",
          "get_aisensy_get_client","get_aisensy_post_client","get_aisensy_patch_client",
          "get_aisensy_client","shutdown_all_clients"]
