from __future__ import annotations

from typing import Any

from .models import LLMResponse


INTERNAL_RESPONSE_KEYS = {
    "raw",
    "reasoning_content",
    "usage",
    "logprobs",
    "system_fingerprint",
    "prompt_tokens_details",
    "completion_tokens_details",
}


def sanitize_raw_payload(value: Any) -> Any:
    """Remove provider internals from nested provider payloads."""
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            if key in INTERNAL_RESPONSE_KEYS:
                continue
            if key == "message" and isinstance(item, dict):
                sanitized[key] = sanitize_raw_payload(item)
            else:
                sanitized[key] = sanitize_raw_payload(item)
        return sanitized

    if isinstance(value, list):
        return [sanitize_raw_payload(item) for item in value]

    return value


def user_response_payload(response: LLMResponse) -> dict[str, Any]:
    """Return the user-facing LLM payload for normal rendering."""
    return {
        "content": response.content,
        "provider": response.provider,
        "model": response.model,
        "success": response.success,
        "error": response.error,
        "created_at": response.created_at,
    }


def debug_response_payload(response: LLMResponse) -> dict[str, Any]:
    """Return a debug payload without chain-of-thought style internals."""
    payload = response.to_dict()
    payload["raw"] = sanitize_raw_payload(payload.get("raw", {}))
    return payload
