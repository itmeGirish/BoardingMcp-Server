"""
LLM service - centralizes model connections.

This module should only build model instances.
Agent-level model assignment lives in each agent node.
"""

from __future__ import annotations

import os
import threading

from langchain_openai import ChatOpenAI

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


def _env_text(name: str, default: str) -> str:
    value = os.getenv(name, "").strip()
    return value or default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name, "").strip()
    if not raw:
        return float(default)
    try:
        return float(raw)
    except ValueError:
        return float(default)


def _build_ollama_model(model_name: str, temperature: float):
    if not model_name:
        return None
    try:
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=model_name,
            temperature=float(temperature),
            reasoning=True,
        )
    except (ImportError, Exception):
        return None


def _build_openai_model():
    try:
        return ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.LLM_MODEL,
            max_completion_tokens=settings.MAX_TOKENS,
        )
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


# Ollama primary + fallback models (configurable by environment variables).
# Default model family:
# - drafting/deep generation: kimi-k2.5:cloud
# - routing/classification:   glm-4.7:cloud
# - fallback:                 glm-4.6:cloud
_primary_drafting_model = _env_text("OLLAMA_PRIMARY_MODEL", "kimi-k2.5:cloud")
_primary_router_model = _env_text("OLLAMA_ROUTER_MODEL", "glm-4.7:cloud")
_fallback_drafting_model = _env_text("OLLAMA_FALLBACK_MODEL", "glm-4.6:cloud")
_fallback_router_model = _env_text("OLLAMA_ROUTER_FALLBACK_MODEL", "glm-4.6:cloud")

_primary_drafting_temp = _env_float("OLLAMA_PRIMARY_TEMPERATURE", 1.0)
_primary_router_temp = _env_float("OLLAMA_ROUTER_TEMPERATURE", 0.7)
_fallback_drafting_temp = _env_float("OLLAMA_FALLBACK_TEMPERATURE", 0.7)
_fallback_router_temp = _env_float("OLLAMA_ROUTER_FALLBACK_TEMPERATURE", _fallback_drafting_temp)

openai_model = _LazyModel("openai_model", _build_openai_model)
nvidia_model = _LazyModel("nvidia_model", _build_nvidia_model)

ollma_fallback_model = _LazyModel(
    "ollma_fallback_model",
    lambda: _build_ollama_model(_fallback_drafting_model, _fallback_drafting_temp),
)
glm_fallback_model = _LazyModel(
    "glm_fallback_model",
    lambda: _build_ollama_model(_fallback_router_model, _fallback_router_temp),
)

ollma_model = _LazyModel(
    "ollma_model",
    lambda: _first_available(
        _build_ollama_model(_primary_drafting_model, _primary_drafting_temp),
        ollma_fallback_model,
        openai_model,
    ),
)
glm_model = _LazyModel(
    "glm_model",
    lambda: _first_available(
        _build_ollama_model(_primary_router_model, _primary_router_temp),
        glm_fallback_model,
        ollma_fallback_model,
        openai_model,
    ),
)


__all__ = [
    "openai_model",
    "nvidia_model",
    "ollma_model",
    "glm_model",
    "ollma_fallback_model",
    "glm_fallback_model",
]
