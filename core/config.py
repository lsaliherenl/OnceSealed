"""Settings loaded from the project's .env file."""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class AISettings:
    base_url: str
    model: str
    api_key: str


def ai_settings() -> AISettings:
    api_key = os.environ.get("OPENROUTER_API_KEY", "")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set in .env")
    return AISettings(
        base_url=os.environ.get("AI_BASE_URL", "https://openrouter.ai/api/v1"),
        model=os.environ.get("AI_MODEL", "typesafe/jev-router"),
        api_key=api_key,
    )
