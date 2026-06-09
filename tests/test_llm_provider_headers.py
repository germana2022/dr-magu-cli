from dr_magu.llm_runtime.openai_compatible import DEFAULT_USER_AGENT, _build_headers


def test_llm_provider_uses_drmagu_user_agent(monkeypatch):
    monkeypatch.delenv("LLM_USER_AGENT", raising=False)
    monkeypatch.delenv("LLM_EXTRA_HEADERS", raising=False)

    headers = _build_headers("secret")

    assert headers["Authorization"] == "Bearer secret"
    assert headers["Content-Type"] == "application/json"
    assert headers["Accept"] == "application/json"
    assert headers["User-Agent"] == DEFAULT_USER_AGENT
    assert not headers["User-Agent"].startswith("Python-urllib")


def test_llm_provider_allows_user_agent_override(monkeypatch):
    monkeypatch.setenv("LLM_USER_AGENT", "custom-agent/1.0")
    monkeypatch.delenv("LLM_EXTRA_HEADERS", raising=False)

    headers = _build_headers("secret")

    assert headers["User-Agent"] == "custom-agent/1.0"


def test_llm_provider_allows_extra_headers(monkeypatch):
    monkeypatch.delenv("LLM_USER_AGENT", raising=False)
    monkeypatch.setenv("LLM_EXTRA_HEADERS", '{"X-Client":"dr-magu","X-Test":"true"}')

    headers = _build_headers("secret")

    assert headers["X-Client"] == "dr-magu"
    assert headers["X-Test"] == "true"
