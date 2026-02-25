"""Top-level app package exports.

Keep imports lazy to avoid side effects (for example DB engine setup)
when modules only need a narrow subpackage like app.agents.*.
"""

from typing import Any

__all__ = [
    "settings",
    "logger",
    "get_session",
    "BusinessCreation",
    "ProjectCreation",
    "User",
    "BusinessCreationRepository",
    "UserCreationRepository",
    "ProjectCreationRepository",
]


def __getattr__(name: str) -> Any:
    if name in {"settings", "logger"}:
        from .config import logger, settings

        return {"settings": settings, "logger": logger}[name]

    if name in {
        "BusinessCreation",
        "ProjectCreation",
        "User",
        "BusinessCreationRepository",
        "UserCreationRepository",
        "ProjectCreationRepository",
        "get_session",
    }:
        from .database import (
            BusinessCreation,
            BusinessCreationRepository,
            ProjectCreation,
            ProjectCreationRepository,
            User,
            UserCreationRepository,
            get_session,
        )

        return {
            "BusinessCreation": BusinessCreation,
            "ProjectCreation": ProjectCreation,
            "User": User,
            "BusinessCreationRepository": BusinessCreationRepository,
            "UserCreationRepository": UserCreationRepository,
            "ProjectCreationRepository": ProjectCreationRepository,
            "get_session": get_session,
        }[name]

    raise AttributeError(f"module 'app' has no attribute '{name}'")
