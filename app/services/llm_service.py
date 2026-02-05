"""
This llm services which contains different models
"""
from langchain_openai import ChatOpenAI
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from ..config import settings

openai_model = ChatOpenAI(api_key=settings.OPENAI_API_KEY,
                 model=settings.LLM_MODEL,max_completion_tokens=settings.MAX_TOKENS)

nvidia_model = ChatNVIDIA(
    model=settings.NVIDIA_MODEL,
    api_key=settings.NVIDIA_API_KEY,
    temperature=settings.NVIDIA_TEMPERATURE,
    top_p=settings.NVIDIA_TOP_P,
    max_completion_tokens=settings.NVIDIA_MAX_COMPLETION_TOKENS,
)


__all__=["openai_model", "nvidia_model"]