"""
image_service.py - Auto-generated
Implement your logic here
"""
from langchain_openai import ChatOpenAI
from ..config import settings,logger

llm = ChatOpenAI(api_key=settings.OPENAI_API_KEY,)


