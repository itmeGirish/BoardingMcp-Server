"""
settings.py - Auto-generated
Implement your logic here
"""

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional

class Settings(BaseSettings):
    # GOOGLE_CLIENT_ID: str
    # GOOGLE_CLIENT_SECRET: str
    # GOOGLE_REDIRECT_URI: str
    # LOCAL_POSTGRES_URL: str  # keep only one field
    # ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    # ALGORITHM: str = "HS256"


    STG_BASE_URL:str
    PARTNER_ID:str
    AiSensy_API_Key:str
    BUSINESS_ID:str
    BASE_URL:str
    Direct_BASE_URL:str

    #database postgres
    db_host:str
    db_port:str
    db_name:str
    db_user:str
    db_password:str







    #Databse connection
    mongodb_uri:str
    mongodb_db_name:str
    data_collection_name:str
    law_collection_name:str

    #logging
    log_level:str

    #logging Dir
    LOG_DIR:str


    #auth
    SECRET_KEY:str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    #openai api keys
    OPENAI_API_KEY:str
    BRAVE_API_KEY: Optional[str] = None

    #nvidia
    NVIDIA_API_KEY:str
    NVIDIA_MODEL:str
    NVIDIA_TEMPERATURE:float
    NVIDIA_TOP_P:float
    NVIDIA_MAX_COMPLETION_TOKENS:int
    
    LLM_MODEL:str
    TEMPERATURE:str
    MAX_TOKENS:int=None
    TIMEOUT:str=None
    MAX_RETRIES:int

    QDRANT_CLIENT_URL:str
    QDRANT_API_KEY: Optional[str] = None
    QUADRANT_CLIENT_URL: Optional[str] = None
    QUADRANT_API_KEY: Optional[str] = None
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"


    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
