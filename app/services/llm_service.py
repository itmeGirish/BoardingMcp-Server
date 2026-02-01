"""
This llm services which contains different models
"""
from langchain_openai import ChatOpenAI
from ..config import settings

openai_model = ChatOpenAI(api_key=settings.OPENAI_API_KEY,
                 model=settings.LLM_MODEL,max_completion_tokens=settings.MAX_TOKENS)



__all__=["openai_model"]