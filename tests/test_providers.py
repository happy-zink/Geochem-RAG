"""Offline tests for the SiliconFlow provider adapter (no network)."""

from __future__ import annotations

import json
import socket
import urllib.error

import pytest

from geochem_rag.providers import (
    KIND_AUTH,
    KIND_BAD_REQUEST,
    KIND_BAD_RESPONSE,
    KIND_NOT_CONFIGURED,
    KIND_RATE_LIMIT,
    KIND_TIMEOUT,
    ChatResult,
    DeepSeekChatClient,
    ProviderConfig,
    ProviderError,
    SiliconFlowClient,
    chat_provider_from_env,
    embedding_provider_from_env,
    list_available_models,
)


class FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


def make_config(**overrides: object) -> ProviderConfig:
    base = dict(
        api_key="secret-key-xyz",
        base_url="https://api.siliconflow.cn/v1",
        chat_model="test-chat",
        embedding_model="test-embed",
        timeout=5.0,
        max_retries=0,
        backoff_seconds=0.0,
    )
    base.update(overrides)
    return ProviderConfig(**base)  # type: ignore[arg-type]


def chat_payload(text: str = "hello") -> bytes:
    return json.dumps(
        {
            "model": "test-chat",
            "choices": [{"message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
            "usage": {"total_tokens": 3},
        }
    ).encode("utf-8")


def test_from_env_reads_values_and_missing_key():
    config = ProviderConfig.from_env({"SILICONFLOW_API_KEY": " k ", "GEOCHEM_CHAT_MODEL": "m1"})
    assert config.api_key == "k"
    assert config.chat_model == "m1"
    assert config.base_url == "https://api.siliconflow.cn/v1"

    empty = ProviderConfig.from_env({})
    assert empty.api_key is None
    with pytest.raises(ProviderError) as excinfo:
        empty.require_key()
    assert excinfo.value.kind == KIND_NOT_CONFIGURED


def test_from_env_parses_disable_proxy_flag():
    assert ProviderConfig.from_env({"GEOCHEM_DISABLE_PROXY": "1"}).disable_proxy is True
    assert ProviderConfig.from_env({"GEOCHEM_DISABLE_PROXY": "no"}).disable_proxy is False


def test_deepseek_and_embedding_use_separate_keys_and_endpoints():
    env = {
        "DEEPSEEK_API_KEY": "deepseek-secret",
        "SILICONFLOW_API_KEY": "silicon-secret",
        "GEOCHEM_CHAT_PROVIDER": "deepseek",
        "GEOCHEM_EMBEDDING_PROVIDER": "siliconflow",
        "GEOCHEM_EMBEDDING_MODEL": "BAAI/bge-m3",
    }
    chat = chat_provider_from_env(env)
    embedder = embedding_provider_from_env(env)
    assert isinstance(chat, DeepSeekChatClient)
    assert chat.config.api_key == "deepseek-secret"
    assert chat.config.base_url == "https://api.deepseek.com"
    assert chat.config.chat_model == "deepseek-chat"
    assert isinstance(embedder, SiliconFlowClient)
    assert embedder.config.api_key == "silicon-secret"
    assert embedder.config.base_url == "https://api.siliconflow.cn/v1"
    assert embedder.config.embedding_model == "BAAI/bge-m3"


def test_deepseek_chat_uses_official_model_and_json_mode():
    captured = {}

    def opener(request, timeout):
        captured["url"] = request.full_url
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        captured["authorization"] = request.get_header("Authorization")
        return FakeResponse(chat_payload('{"status":"answered"}'))

    config = ProviderConfig.from_deepseek_env({"DEEPSEEK_API_KEY": "deepseek-secret"})
    client = DeepSeekChatClient(config, opener=opener)
    result = client.chat([{"role": "user", "content": "reply in JSON"}], json_mode=True)
    assert result.text == '{"status":"answered"}'
    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["payload"]["model"] == "deepseek-chat"
    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert captured["authorization"] == "Bearer deepseek-secret"


def test_missing_deepseek_key_has_correct_error_name():
    config = ProviderConfig.from_deepseek_env({"SILICONFLOW_API_KEY": "silicon-only"})
    with pytest.raises(ProviderError, match="DEEPSEEK_API_KEY"):
        config.require_key()


def test_chat_success_parses_result():
    client = SiliconFlowClient(make_config(), opener=lambda request, timeout: FakeResponse(chat_payload("ok")))
    result = client.chat([{"role": "user", "content": "hi"}])
    assert isinstance(result, ChatResult)
    assert result.text == "ok"
    assert result.usage["total_tokens"] == 3


def test_auth_error_is_not_retried_and_hides_key():
    calls = {"n": 0}

    def opener(request, timeout):
        calls["n"] += 1
        raise urllib.error.HTTPError(request.full_url, 401, "Unauthorized", {}, None)

    client = SiliconFlowClient(make_config(max_retries=3), opener=opener)
    with pytest.raises(ProviderError) as excinfo:
        client.chat([{"role": "user", "content": "hi"}])
    assert excinfo.value.kind == KIND_AUTH
    assert excinfo.value.retryable is False
    assert calls["n"] == 1
    assert "secret-key-xyz" not in str(excinfo.value)


def test_rate_limit_is_retried_then_succeeds():
    calls = {"n": 0}
    sleeps: list[float] = []

    def opener(request, timeout):
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.HTTPError(request.full_url, 429, "Too Many Requests", {}, None)
        return FakeResponse(chat_payload("after-retry"))

    client = SiliconFlowClient(
        make_config(max_retries=2, backoff_seconds=0.01),
        opener=opener,
        sleeper=sleeps.append,
    )
    result = client.chat([{"role": "user", "content": "hi"}])
    assert result.text == "after-retry"
    assert calls["n"] == 2
    assert sleeps == [0.01]


def test_timeout_maps_to_timeout_kind():
    def opener(request, timeout):
        raise urllib.error.URLError(socket.timeout("timed out"))

    client = SiliconFlowClient(make_config(max_retries=0), opener=opener)
    with pytest.raises(ProviderError) as excinfo:
        client.chat([{"role": "user", "content": "hi"}])
    assert excinfo.value.kind == KIND_TIMEOUT
    assert excinfo.value.retryable is True


def test_bad_response_on_invalid_json():
    client = SiliconFlowClient(
        make_config(), opener=lambda request, timeout: FakeResponse(b"not json")
    )
    with pytest.raises(ProviderError) as excinfo:
        client.chat([{"role": "user", "content": "hi"}])
    assert excinfo.value.kind == KIND_BAD_RESPONSE


def test_bad_request_on_422():
    def opener(request, timeout):
        raise urllib.error.HTTPError(request.full_url, 422, "Unprocessable", {}, None)

    client = SiliconFlowClient(make_config(), opener=opener)
    with pytest.raises(ProviderError) as excinfo:
        client.chat([{"role": "user", "content": "hi"}])
    assert excinfo.value.kind == KIND_BAD_REQUEST


def test_embed_batches_and_preserves_order():
    seen_batches: list[list[str]] = []

    def opener(request, timeout):
        payload = json.loads(request.data.decode("utf-8"))
        batch = payload["input"]
        seen_batches.append(batch)
        data = [
            {"index": i, "embedding": [float(len(text)), 1.0]} for i, text in enumerate(batch)
        ]
        return FakeResponse(json.dumps({"data": data}).encode("utf-8"))

    client = SiliconFlowClient(make_config(), opener=opener, embedding_batch_size=2)
    vectors = client.embed(["a", "bb", "ccc"])
    assert [len(b) for b in seen_batches] == [2, 1]
    assert vectors == [[1.0, 1.0], [2.0, 1.0], [3.0, 1.0]]


def test_embed_empty_input_makes_no_call():
    def opener(request, timeout):
        raise AssertionError("should not be called")

    client = SiliconFlowClient(make_config(), opener=opener)
    assert client.embed([]) == []


def test_list_available_models_returns_ids():
    payload = json.dumps({"data": [{"id": "m1"}, {"id": "m2"}]}).encode("utf-8")
    import geochem_rag.providers as providers

    original = providers.urllib.request.urlopen
    providers.urllib.request.urlopen = lambda request, timeout: FakeResponse(payload)
    try:
        ids = list_available_models(make_config())
    finally:
        providers.urllib.request.urlopen = original
    assert ids == ["m1", "m2"]
