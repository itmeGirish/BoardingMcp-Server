from dataclasses import replace
from ....config import logger
from ....database import qdrant_db
from ....utils.draftingAgent import get_active_qdrant_profile, retrieve_drafting_context


async def DraftingRAGTool(query: str, collection_name: str = "") -> str:
    """
    Retrieve drafting context from Qdrant.

    Args:
        query: User query text.
        collection_name: Optional explicit Qdrant collection name. If empty,
            the active profile/default collection is used.
    """

    try:
        profile = get_active_qdrant_profile()
        if collection_name and collection_name.strip():
            profile = replace(profile, collection_name=collection_name.strip())
        return await retrieve_drafting_context(
            query=query,
            qdrant_db=qdrant_db,
            profile=profile,
        )
    except Exception as exc:
        logger.error("DraftingRAGTool execution failed: %s: %s", type(exc).__name__, exc)
        return "Error: Unable to retrieve documents."
