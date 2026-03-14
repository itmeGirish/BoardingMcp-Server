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

    embeddings_model_name:str







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
    DRAFT_LLM_MODEL: Optional[str] = None  # Separate model for draft node; defaults to LLM_MODEL
    REVIEW_LLM_MODEL: Optional[str] = None  # Separate model for review node; defaults to LLM_MODEL
    REVIEW_MAX_TOKENS: Optional[int] = None  # max_completion_tokens for review model; defaults to MAX_TOKENS. Increase for v5.0 longer drafts.
    REVIEW_REASONING_EFFORT: Optional[str] = "medium"  # "low", "medium", "high" — enables reasoning for review model
    TEMPERATURE:str
    MAX_TOKENS:int=None
    TIMEOUT:str=None
    MAX_RETRIES:int

    QDRANT_CLIENT_URL:str
    QDRANT_API_KEY: Optional[str] = None
    QUADRANT_CLIENT_URL: Optional[str] = None
    QUADRANT_API_KEY: Optional[str] = None
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    # Drafting pipeline tuning (override in .env without code changes)
    DRAFTING_MAX_REVIEW_CYCLES: int = 1
    DRAFTING_REVIEW_RAG_LIMIT: int = 5
    DRAFTING_WEBSEARCH_SOURCE_URLS: int = 3
    # Pass-1 draft context limits — top-N highest-scored chunks/rules sent to draft LLM.
    # Top-10 chunks are highest Qdrant-scored; reducing cuts input tokens on cloud inference.
    DRAFTING_DRAFT_RAG_LIMIT: int = 0
    DRAFTING_DRAFT_RULES_LIMIT: int = 5

    # Review inline-fix: when True the review node generates a corrected final_artifacts[]
    # alongside blocking_issues[], eliminating the separate pass-2 draft LLM call.
    # Set DRAFTING_REVIEW_INLINE_FIX=false in .env to revert to review-then-redraft.
    DRAFTING_REVIEW_INLINE_FIX: bool = True

    DRAFTING_SKIP_REVIEW: bool = False                  # keep review ON for quality; set True to skip for speed
    DRAFTING_SKIP_REVIEW_AFTER_VALIDATION_IF_CLEAN: bool = True  # skip review only after deterministic gates/citation checks pass cleanly

    # v8.1 Template Engine
    TEMPLATE_ENGINE_ENABLED: bool = False               # True=v8.1 template+gap-fill, False=v5.0 freetext

    # v5.0 enrichment settings
    DRAFTING_ENRICHMENT_LLM_ENABLED: bool = True     # use LLM for limitation article selection
    DRAFTING_CITATION_VALIDATOR_ENABLED: bool = True  # validate cited provisions against enrichment
    DRAFTING_USER_REQUEST_ENTITY_MINING: bool = True  # mine amounts/dates/refs from user_request text
    DRAFTING_RAG_ENABLED: bool = False                 # False=skip RAG node entirely (no Qdrant/OpenAI calls)
    DRAFTING_RAG_PROVISION_SCAN: bool = True          # scan RAG chunks for statutory section numbers
    DRAFTING_LIMITATION_RETRY: bool = False            # disabled for speed — skip retry web search
    DRAFTING_LIMITATION_COMMON_FALLBACK: bool = True  # use common articles as last-resort fallback
    DRAFTING_PROCEDURAL_SEARCH: bool = False           # disabled for speed — skip slow web search
    DRAFTING_LEGAL_RESEARCH_ENABLED: bool = False     # False=skip LegalResearch websearch (Brave API)

    # Ollama model configuration (override in .env)
    OLLAMA_PRIMARY_MODEL: str = "glm-5:cloud"               # deep generation (intake fallback, general)
    OLLAMA_ROUTER_MODEL: str = "glm-4.7:cloud"             # routing / classification
    OLLAMA_INTAKE_MODEL: str = "qwen3.5:cloud"              # intake node
    OLLAMA_DRAFT_MODEL: str = "qwen3.5:cloud"                # draft node
    OLLAMA_REVIEW_MODEL: str = "glm-5:cloud"                  # review node
    OLLAMA_FALLBACK_MODEL: str = "glm-4.6:cloud"           # fallback for drafting chain
    OLLAMA_ROUTER_FALLBACK_MODEL: str = "glm-4.6:cloud"    # fallback for router chain

    # Ollama temperatures
    OLLAMA_PRIMARY_TEMPERATURE: float = 0.7
    OLLAMA_ROUTER_TEMPERATURE: float = 0.3
    OLLAMA_INTAKE_TEMPERATURE: float = 0.3
    OLLAMA_DRAFT_TEMPERATURE: float = 0.7
    OLLAMA_REVIEW_TEMPERATURE: float = 0.3
    OLLAMA_FALLBACK_TEMPERATURE: float = 0.7
    OLLAMA_ROUTER_FALLBACK_TEMPERATURE: float = 0.3

    # Ollama reasoning flags (chain-of-thought)
    # Only enable reasoning for nodes that need deep legal thinking (draft, review).
    # Intake/router/enrichment do simple extraction — reasoning just adds latency.
    OLLAMA_DRAFTING_REASONING: bool = False
    OLLAMA_ROUTER_REASONING: bool = False
    OLLAMA_INTAKE_REASONING: bool = False
    OLLAMA_DRAFT_REASONING: bool = True
    OLLAMA_REVIEW_REASONING: bool = True

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
