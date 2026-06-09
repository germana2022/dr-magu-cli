from dr_magu.brain.models import ResolvedModelConfig
from dr_magu.llm_runtime.models import LLMMessage, LLMResponse
from dr_magu.llm_runtime.runtime import LLMRuntime
from dr_magu.llm_runtime.sanitizer import debug_response_payload, sanitize_raw_payload, user_response_payload


class FakeReasoningProvider:
    def chat(self, model_config: ResolvedModelConfig, messages: list[LLMMessage], timeout_seconds: int = 60) -> LLMResponse:
        return LLMResponse(
            content="Hello from Dr Magu.",
            provider=model_config.provider,
            model=model_config.model,
            raw={
                "id": "abc",
                "choices": [
                    {
                        "message": {
                            "content": "Hello from Dr Magu.",
                            "reasoning_content": "private reasoning",
                        },
                        "logprobs": None,
                    }
                ],
                "usage": {"total_tokens": 10},
                "system_fingerprint": "fp_demo",
            },
        )


def test_user_response_payload_excludes_raw_and_usage():
    response = LLMResponse(
        content="Hello",
        provider="opencode",
        model="deepseek-v4-flash",
        raw={"usage": {"total_tokens": 10}, "reasoning_content": "hidden"},
    )

    payload = user_response_payload(response)

    assert payload["content"] == "Hello"
    assert "raw" not in payload
    assert "usage" not in payload
    assert "reasoning_content" not in payload


def test_debug_response_payload_sanitizes_reasoning_and_usage():
    response = LLMResponse(
        content="Hello",
        provider="opencode",
        model="deepseek-v4-flash",
        raw={
            "choices": [{"message": {"content": "Hello", "reasoning_content": "hidden"}}],
            "usage": {"total_tokens": 10},
            "system_fingerprint": "fp",
        },
    )

    payload = debug_response_payload(response)

    assert "usage" not in payload["raw"]
    assert "system_fingerprint" not in payload["raw"]
    assert "reasoning_content" not in str(payload)


def test_sanitize_raw_payload_removes_nested_internal_keys():
    payload = {
        "choices": [{"message": {"content": "Hi", "reasoning_content": "secret"}}],
        "usage": {"total_tokens": 123},
    }

    sanitized = sanitize_raw_payload(payload)

    assert "usage" not in sanitized
    assert "reasoning_content" not in str(sanitized)


def test_llm_runtime_normal_response_is_sanitized(tmp_path):
    result = LLMRuntime(tmp_path, provider=FakeReasoningProvider()).chat("hi")

    assert result.success is True
    assert result.data["response"]["content"] == "Hello from Dr Magu."
    assert "raw" not in result.data["response"]
    assert "reasoning_content" not in str(result.data["response"])
    assert "reasoning_content" not in str(result.data["debug"])
    assert "usage" not in str(result.data["debug"])
