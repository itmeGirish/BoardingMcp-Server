"""
LLM service — centralizes all model connections.

This file is ONLY for LLM instance creation.
Agent-specific model mapping lives in each agent's base_agent folder.
"""
from langchain_openai import ChatOpenAI
from ..config import settings


# ── OpenAI ───────────────────────────────────────────────────────
openai_model = ChatOpenAI(
    api_key=settings.OPENAI_API_KEY,
    model=settings.LLM_MODEL,
    max_completion_tokens=settings.MAX_TOKENS,
)

# ── NVIDIA ───────────────────────────────────────────────────────
nvidia_model = None
try:
    from langchain_nvidia_ai_endpoints import ChatNVIDIA
    nvidia_model = ChatNVIDIA(
        model=settings.NVIDIA_MODEL,
        api_key=settings.NVIDIA_API_KEY,
        temperature=settings.NVIDIA_TEMPERATURE,
        top_p=settings.NVIDIA_TOP_P,
        max_completion_tokens=settings.NVIDIA_MAX_COMPLETION_TOKENS,
    )
except (ImportError, Exception):
    pass

# ── Ollama: Kimi K2.5 ───────────────────────────────────────────
ollma_model = None
try:
    from langchain_ollama import ChatOllama
    ollma_model = ChatOllama(
        model="kimi-k2.5:cloud",
        temperature=1,
    )
except (ImportError, Exception):
    pass

# ── Ollama: GLM-4.7 ─────────────────────────────────────────────
glm_model = None
try:
    from langchain_ollama import ChatOllama as _ChatOllama
    glm_model = _ChatOllama(
        model="glm-4.7:cloud",
        temperature=0.7,
    )
except (ImportError, Exception):
    pass


__all__ = ["openai_model", "nvidia_model", "ollma_model", "glm_model"]
