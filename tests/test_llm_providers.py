import pytest

from anjalikastra.llm.client import LLMClient, LLMUnavailable, resolve_provider

_LLM_ENV_VARS = ("WEBTEST_AGENT_LLM_PROVIDER", "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENAI_BASE_URL")


@pytest.fixture(autouse=True)
def clean_llm_env(monkeypatch):
    for var in _LLM_ENV_VARS:
        monkeypatch.delenv(var, raising=False)


def test_no_credentials_resolves_to_no_provider():
    assert resolve_provider() is None


def test_anthropic_key_auto_detects_anthropic(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert resolve_provider() == "anthropic"


def test_openai_key_auto_detects_openai(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert resolve_provider() == "openai"


def test_base_url_alone_auto_detects_openai_for_local_servers(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:11434/v1")  # e.g. Ollama
    assert resolve_provider() == "openai"


def test_anthropic_wins_when_both_are_configured(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    assert resolve_provider() == "anthropic"


def test_explicit_provider_overrides_auto_detection(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    assert resolve_provider("openai") == "openai"


def test_env_provider_overrides_auto_detection(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("WEBTEST_AGENT_LLM_PROVIDER", "openai")
    assert resolve_provider() == "openai"


def test_unknown_provider_is_rejected():
    with pytest.raises(ValueError, match="unknown LLM provider"):
        resolve_provider("gemini-direct")


def test_client_unavailable_without_credentials():
    client = LLMClient("cheap", "capable")
    assert not client.available
    with pytest.raises(LLMUnavailable):
        client.complete("cheap", system="s", prompt="p")


def test_client_available_with_openai_base_url_and_no_key(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
    client = LLMClient("llama3.2", "qwen2.5-coder")
    assert client.available
    assert client.provider == "openai"


def test_openai_compatible_wire_path_end_to_end(monkeypatch):
    """Drive a real completion through a local fake OpenAI-compatible server —
    the same shape Ollama/OpenRouter/Gemini-compat/vLLM speak."""
    import json
    import threading
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class FakeOpenAI(BaseHTTPRequestHandler):
        def log_message(self, *args):  # noqa: A002
            pass

        def do_POST(self):  # noqa: N802
            assert self.path.endswith("/chat/completions")
            body = json.dumps({
                "id": "chatcmpl-1",
                "object": "chat.completion",
                "model": "fake-model",
                "choices": [{"index": 0, "message": {"role": "assistant", "content": "hello from fake"},
                              "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10},
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOpenAI)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        monkeypatch.setenv("OPENAI_BASE_URL", f"http://127.0.0.1:{server.server_address[1]}/v1")
        client = LLMClient("fake-model", "fake-model")
        text = client.complete("cheap", system="s", prompt="p")

        assert text == "hello from fake"
        assert client.ledger.cheap.calls == 1
        assert client.ledger.cheap.input_tokens == 7
        assert client.ledger.cheap.output_tokens == 3
    finally:
        server.shutdown()
        server.server_close()


def test_provider_error_degrades_to_llm_unavailable(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:1/v1")  # nothing listening
    client = LLMClient("fake-model", "fake-model")
    with pytest.raises(LLMUnavailable):
        client.complete("cheap", system="s", prompt="p")
