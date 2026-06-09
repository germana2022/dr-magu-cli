from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from dr_magu.brain.models import ResolvedModelConfig

from .models import LLMMessage, LLMResponse


DEFAULT_USER_AGENT = "dr-magu-cli/1.1.3"


def _build_headers(api_key: str) -> dict[str, str]:
    """Build provider-compatible headers for OpenAI-compatible endpoints.

    Some public providers, including OpenCode gateway endpoints, reject the
    default Python urllib User-Agent through Cloudflare. A stable application
    User-Agent keeps the request explicit and avoids Python's default signature.
    """

    user_agent = os.getenv("LLM_USER_AGENT") or DEFAULT_USER_AGENT
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": user_agent,
    }

    # Optional extra headers in JSON format:
    # LLM_EXTRA_HEADERS='{"X-Client":"dr-magu"}'
    extra_headers = os.getenv("LLM_EXTRA_HEADERS")
    if extra_headers:
        try:
            parsed: Any = json.loads(extra_headers)
            if isinstance(parsed, dict):
                for key, value in parsed.items():
                    if key and value is not None:
                        headers[str(key)] = str(value)
        except json.JSONDecodeError:
            # Ignore invalid optional headers to avoid breaking normal chat.
            pass

    return headers


class OpenAICompatibleProvider:
    """OpenAI-compatible chat completions provider.

    Works with providers exposing `/chat/completions`, including OpenCode/OpenRouter-
    style endpoints configured through the default model settings.
    """

    def chat(self, model_config: ResolvedModelConfig, messages: list[LLMMessage], timeout_seconds: int = 60) -> LLMResponse:
        if not model_config.base_url:
            return LLMResponse(
                content="",
                provider=model_config.provider,
                model=model_config.model,
                success=False,
                error="LLM base_url is required.",
            )

        api_key = os.getenv(model_config.api_key_env or "LLM_API_KEY")
        if not api_key:
            return LLMResponse(
                content="",
                provider=model_config.provider,
                model=model_config.model,
                success=False,
                error=f"Missing API key environment variable: {model_config.api_key_env}",
            )

        base_url = model_config.base_url.rstrip("/")
        url = base_url if base_url.endswith("/chat/completions") else f"{base_url}/chat/completions"

        payload = {
            "model": model_config.model,
            "temperature": model_config.temperature,
            "messages": [message.to_dict() for message in messages],
        }

        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=_build_headers(api_key),
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
                raw_text = response.read().decode("utf-8")
                raw = json.loads(raw_text) if raw_text else {}
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            return LLMResponse(
                content="",
                provider=model_config.provider,
                model=model_config.model,
                success=False,
                error=f"HTTP {exc.code}: {body}",
            )
        except Exception as exc:
            return LLMResponse(
                content="",
                provider=model_config.provider,
                model=model_config.model,
                success=False,
                error=str(exc),
            )

        content = ""
        try:
            content = raw["choices"][0]["message"]["content"]
        except Exception:
            content = raw.get("content") or raw.get("text") or ""

        return LLMResponse(
            content=str(content),
            provider=model_config.provider,
            model=model_config.model,
            success=bool(content),
            error=None if content else "LLM response did not include message content.",
            raw=raw,
        )
