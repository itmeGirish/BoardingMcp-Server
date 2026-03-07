"""Model routing — select the right Ollama Cloud model based on complexity.

Deterministic, no LLM calls. Runs in Stage 0.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from .complexity import Tier

Tier_ = Literal["SIMPLE", "MEDIUM", "COMPLEX"]


@dataclass(frozen=True)
class ModelRoute:
    """Routing decision for a single document."""
    model: str
    tier: Tier_
    reasoning: bool
    temperature: float
    source: str  # "tier", "cause_override", "fallback"


# Default model per tier
MODEL_ROUTES: dict[str, dict] = {
    "SIMPLE": {"model": "glm-4.7:cloud", "reasoning": False, "temperature": 0.5},
    "MEDIUM": {"model": "qwen3.5:cloud", "reasoning": True, "temperature": 0.7},
    "COMPLEX": {"model": "glm-5:cloud", "reasoning": True, "temperature": 0.7},
}

# Cause types that always use a specific tier regardless of score
CAUSE_TYPE_OVERRIDES: dict[str, str] = {
    "partition": "glm-5:cloud",
    "motor_accident": "glm-5:cloud",
    "partnership_dissolution": "glm-5:cloud",
    "ni_138_complaint": "glm-4.7:cloud",
    "summary_suit_cheque": "glm-4.7:cloud",
}

# Fallback chain when primary model is unavailable
FALLBACK_CHAIN: dict[str, list[str]] = {
    "glm-5:cloud": ["deepseek-v3.2:cloud", "qwen3.5:cloud"],
    "qwen3.5:cloud": ["deepseek-v3.2:cloud", "glm-4.7:cloud"],
    "glm-4.7:cloud": ["qwen3-next:cloud"],
}


def route_model(
    tier: Tier_,
    cause_type: str | None = None,
) -> ModelRoute:
    """Select model based on complexity tier and optional cause type override.

    Args:
        tier: SIMPLE, MEDIUM, or COMPLEX from complexity scoring
        cause_type: Optional cause type for override lookup

    Returns:
        ModelRoute with model name, reasoning flag, temperature, source
    """
    # Check cause type override first
    if cause_type and cause_type in CAUSE_TYPE_OVERRIDES:
        override_model = CAUSE_TYPE_OVERRIDES[cause_type]
        # Find the tier config that matches this model
        for t, cfg in MODEL_ROUTES.items():
            if cfg["model"] == override_model:
                return ModelRoute(
                    model=override_model,
                    tier=t,  # type: ignore[arg-type]
                    reasoning=cfg["reasoning"],
                    temperature=cfg["temperature"],
                    source="cause_override",
                )
        # If model not in standard tiers, use COMPLEX defaults
        return ModelRoute(
            model=override_model,
            tier="COMPLEX",
            reasoning=True,
            temperature=0.7,
            source="cause_override",
        )

    # Standard tier-based routing
    cfg = MODEL_ROUTES[tier]
    return ModelRoute(
        model=cfg["model"],
        tier=tier,
        reasoning=cfg["reasoning"],
        temperature=cfg["temperature"],
        source="tier",
    )


def get_fallbacks(model: str) -> list[str]:
    """Get fallback models for a given primary model."""
    return list(FALLBACK_CHAIN.get(model, []))
