"""OpenAI-compatible chat client (OpenRouter by default).

The model is configuration, not code: switching from Jev Router to another
model or our own endpoint only changes AI_BASE_URL / AI_MODEL in .env.
"""

from dataclasses import dataclass
from typing import Any

from openai import OpenAI

from core.config import AISettings, ai_settings


@dataclass(frozen=True)
class Completion:
    content: str
    requested_model: str
    served_model: str | None
    usage: dict[str, Any] | None
    router_metadata: Any
    raw: dict[str, Any]


class ChatClient:
    def __init__(self, settings: AISettings | None = None):
        self.settings = settings or ai_settings()
        self._client = OpenAI(
            base_url=self.settings.base_url,
            api_key=self.settings.api_key,
            default_headers={
                "X-OpenRouter-Metadata": "enabled",  # report which model the router picked
                "X-Title": "OnceSealed",
            },
        )

    def complete_json(
        self,
        system: str,
        user: str,
        schema_name: str,
        schema: dict[str, Any],
        max_tokens: int = 4000,
        seed: int = 7,
    ) -> Completion:
        resp = self._client.chat.completions.create(
            model=self.settings.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0,
            seed=seed,
            max_tokens=max_tokens,
            response_format={
                "type": "json_schema",
                "json_schema": {"name": schema_name, "strict": True, "schema": schema},
            },
            extra_body={"usage": {"include": True}},
        )
        raw = resp.model_dump()
        return Completion(
            content=resp.choices[0].message.content or "",
            requested_model=self.settings.model,
            served_model=raw.get("model"),
            usage=raw.get("usage"),
            router_metadata=raw.get("openrouter_metadata"),
            raw=raw,
        )
