"""
LLM service - centralizes model connections.

This module should only build model instances.
Agent-level model assignment lives in each agent node.
All configuration comes from settings.py — no os.getenv() or hardcoded values.
"""

from __future__ import annotations

import threading

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from ..config import settings


class _LazyModel:
    """Thread-safe lazy model wrapper.

    Defers provider/client initialization until the model is actually used.
    """

    def __init__(self, name: str, factory):
        self._name = name
        self._factory = factory
        self._model = None
        self._loaded = False
        self._lock = threading.Lock()

    def resolve_model(self):
        if self._loaded:
            return self._model
        with self._lock:
            if not self._loaded:
                try:
                    self._model = self._factory()
                except Exception:
                    self._model = None
                self._loaded = True
        return self._model

    def bind_tools(self, *args, **kwargs):
        model = self.resolve_model()
        if model is None:
            return None
        return model.bind_tools(*args, **kwargs)

    def __getattr__(self, name):
        model = self.resolve_model()
        if model is None:
            raise AttributeError(f"Model '{self._name}' is unavailable; missing attribute '{name}'")
        return getattr(model, name)

    def __repr__(self) -> str:
        status = "loaded" if self._loaded else "lazy"
        return f"_LazyModel(name={self._name!r}, status={status})"


# ---------------------------------------------------------------------------
# Ollama builder
# ---------------------------------------------------------------------------

def _build_ollama_model(
    model_name: str,
    temperature: float,
    reasoning: bool = True,
    format: str | None = None,
):
    if not model_name:
        return None
    try:
        from langchain_ollama import ChatOllama

        kwargs = dict(
            model=model_name,
            temperature=float(temperature),
            reasoning=reasoning,
        )
        # IMPORTANT: format="json" suppresses <think> token probability to zero
        # on Ollama (GitHub issue #10538), silently disabling chain-of-thought.
        # When reasoning is enabled, skip format constraint — LangChain's
        # .with_structured_output() handles JSON extraction instead.
        if format and not reasoning:
            kwargs["format"] = format
        return ChatOllama(**kwargs)
    except (ImportError, Exception):
        return None


# ---------------------------------------------------------------------------
# OpenAI builders
# ---------------------------------------------------------------------------

def _build_openai_model():
    try:
        return ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.LLM_MODEL,
            max_completion_tokens=settings.MAX_TOKENS,
        )
    except Exception:
        return None


def _build_draft_openai_model():
    """OpenAI fallback for draft node."""
    model_name = settings.DRAFT_LLM_MODEL or settings.LLM_MODEL
    try:
        return ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=model_name,
            max_completion_tokens=settings.MAX_TOKENS,
        )
    except Exception:
        return None


def _build_review_openai_model():
    """OpenAI fallback for review node."""
    model_name = settings.REVIEW_LLM_MODEL or settings.LLM_MODEL
    reasoning = settings.REVIEW_REASONING_EFFORT
    max_tokens = settings.REVIEW_MAX_TOKENS or settings.MAX_TOKENS
    try:
        kwargs = dict(
            api_key=settings.OPENAI_API_KEY,
            model=model_name,
            max_completion_tokens=max_tokens,
        )
        if reasoning:
            kwargs["model_kwargs"] = {"reasoning_effort": reasoning}
        return ChatOpenAI(**kwargs)
    except Exception:
        return None


def _build_nvidia_model():
    try:
        from langchain_nvidia_ai_endpoints import ChatNVIDIA

        return ChatNVIDIA(
            model=settings.NVIDIA_MODEL,
            api_key=settings.NVIDIA_API_KEY,
            temperature=settings.NVIDIA_TEMPERATURE,
            top_p=settings.NVIDIA_TOP_P,
            max_completion_tokens=settings.NVIDIA_MAX_COMPLETION_TOKENS,
        )
    except (ImportError, Exception):
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_candidate(candidate):
    if isinstance(candidate, _LazyModel):
        return candidate.resolve_model()
    return candidate


def _first_available(*candidates):
    for candidate in candidates:
        model = _resolve_candidate(candidate)
        if model is not None:
            return model
    return None


# ---------------------------------------------------------------------------
# OpenAI models (fallbacks)
# ---------------------------------------------------------------------------

openai_model = _LazyModel("openai_model", _build_openai_model)
draft_openai_model = _LazyModel("draft_openai_model", _build_draft_openai_model)
review_openai_model = _LazyModel("review_openai_model", _build_review_openai_model)
nvidia_model = _LazyModel("nvidia_model", _build_nvidia_model)

# ---------------------------------------------------------------------------
# Ollama models — all config from settings.*
# ---------------------------------------------------------------------------

# Intake: qwen3.5:cloud (reasoning + JSON) → fallback glm_model → OpenAI
intake_ollama_model = _LazyModel(
    "intake_ollama_model",
    lambda: _first_available(
        _build_ollama_model(
            settings.OLLAMA_INTAKE_MODEL,
            settings.OLLAMA_INTAKE_TEMPERATURE,
            reasoning=settings.OLLAMA_INTAKE_REASONING,
            format="json",
        ),
        openai_model,
    ),
)

# Draft: glm-5:cloud (reasoning, #1 intelligence) → fallback OpenAI
# No format="json" — reasoning=True needs <think> tokens; LangChain handles JSON.
draft_ollama_model = _LazyModel(
    "draft_ollama_model",
    lambda: _first_available(
        _build_ollama_model(
            settings.OLLAMA_DRAFT_MODEL,
            settings.OLLAMA_DRAFT_TEMPERATURE,
            reasoning=settings.OLLAMA_DRAFT_REASONING,
        ),
        draft_openai_model,
    ),
)

# Review: qwen3.5:cloud (reasoning, low hallucination) → fallback OpenAI
# No format="json" — reasoning=True needs <think> tokens; LangChain handles JSON.
review_ollama_model = _LazyModel(
    "review_ollama_model",
    lambda: _first_available(
        _build_ollama_model(
            settings.OLLAMA_REVIEW_MODEL,
            settings.OLLAMA_REVIEW_TEMPERATURE,
            reasoning=settings.OLLAMA_REVIEW_REASONING,
        ),
        review_openai_model,
    ),
)

# Fallback models
ollma_fallback_model = _LazyModel(
    "ollma_fallback_model",
    lambda: _build_ollama_model(
        settings.OLLAMA_FALLBACK_MODEL,
        settings.OLLAMA_FALLBACK_TEMPERATURE,
        reasoning=settings.OLLAMA_DRAFTING_REASONING,
    ),
)
glm_fallback_model = _LazyModel(
    "glm_fallback_model",
    lambda: _build_ollama_model(
        settings.OLLAMA_ROUTER_FALLBACK_MODEL,
        settings.OLLAMA_ROUTER_FALLBACK_TEMPERATURE,
        reasoning=settings.OLLAMA_ROUTER_REASONING,
    ),
)

# General-purpose Ollama: glm-5:cloud → fallback chain → OpenAI
ollma_model = _LazyModel(
    "ollma_model",
    lambda: _first_available(
        _build_ollama_model(
            settings.OLLAMA_PRIMARY_MODEL,
            settings.OLLAMA_PRIMARY_TEMPERATURE,
            reasoning=settings.OLLAMA_DRAFTING_REASONING,
        ),
        ollma_fallback_model,
        openai_model,
    ),
)

# Router: glm-4.7:cloud → fallback chain → OpenAI
glm_model = _LazyModel(
    "glm_model",
    lambda: _first_available(
        _build_ollama_model(
            settings.OLLAMA_ROUTER_MODEL,
            settings.OLLAMA_ROUTER_TEMPERATURE,
            reasoning=settings.OLLAMA_ROUTER_REASONING,
        ),
        glm_fallback_model,
        ollma_fallback_model,
        openai_model,
    ),
)


__all__ = [
    "openai_model",
    "draft_openai_model",
    "draft_ollama_model",
    "review_openai_model",
    "review_ollama_model",
    "nvidia_model",
    "ollma_model",
    "glm_model",
    "ollma_fallback_model",
    "glm_fallback_model",
    "embeddings_model",
]

embeddings_model = OpenAIEmbeddings(
    api_key=settings.OPENAI_API_KEY,
    model=settings.embeddings_model_name,
)
