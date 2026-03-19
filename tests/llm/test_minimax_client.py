# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for MiniMax LLM client.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from omegaconf import OmegaConf

from miroflow.llm.minimax_client import (
    MINIMAX_MODELS,
    MINIMAX_TEMP_MAX,
    MINIMAX_TEMP_MIN,
    MiniMaxClient,
    _clamp_temperature,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_config(**overrides):
    """Create a valid MiniMaxClient DictConfig."""
    defaults = {
        "provider_class": "MiniMaxClient",
        "model_name": "MiniMax-M2.7",
        "api_key": "test-key",
        "base_url": "https://api.minimax.io/v1",
        "temperature": 1.0,
        "top_p": 0.95,
        "min_p": 0.0,
        "top_k": -1,
        "max_tokens": 32000,
        "max_context_length": 204800,
        "async_client": True,
        "reasoning_effort": None,
        "repetition_penalty": 1.0,
        "disable_cache_control": True,
        "keep_tool_result": -1,
        "use_tool_calls": False,
    }
    defaults.update(overrides)
    return OmegaConf.create(defaults)


@pytest.fixture
def minimax_cfg():
    return _make_config()


@pytest.fixture
def minimax_sync_cfg():
    return _make_config(async_client=False)


# ---------------------------------------------------------------------------
# Temperature clamping
# ---------------------------------------------------------------------------

class TestClampTemperature:
    def test_zero_clamped_to_min(self):
        assert _clamp_temperature(0.0) == MINIMAX_TEMP_MIN

    def test_negative_clamped_to_min(self):
        assert _clamp_temperature(-0.5) == MINIMAX_TEMP_MIN

    def test_above_max_clamped(self):
        assert _clamp_temperature(2.0) == MINIMAX_TEMP_MAX

    def test_within_range_unchanged(self):
        assert _clamp_temperature(0.5) == 0.5

    def test_max_boundary(self):
        assert _clamp_temperature(1.0) == 1.0

    def test_just_above_zero(self):
        assert _clamp_temperature(0.01) == 0.01


# ---------------------------------------------------------------------------
# Client instantiation
# ---------------------------------------------------------------------------

class TestMiniMaxClientInit:
    def test_creates_async_client(self, minimax_cfg):
        client = MiniMaxClient(minimax_cfg)
        assert client.model_name == "MiniMax-M2.7"
        assert client.async_client is True
        from openai import AsyncOpenAI
        assert isinstance(client.client, AsyncOpenAI)

    def test_creates_sync_client(self, minimax_sync_cfg):
        client = MiniMaxClient(minimax_sync_cfg)
        assert client.async_client is False
        from openai import OpenAI
        assert isinstance(client.client, OpenAI)

    def test_highspeed_model(self):
        cfg = _make_config(model_name="MiniMax-M2.7-highspeed")
        client = MiniMaxClient(cfg)
        assert client.model_name == "MiniMax-M2.7-highspeed"

    def test_custom_base_url(self):
        cfg = _make_config(base_url="https://api.minimaxi.com/v1")
        client = MiniMaxClient(cfg)
        assert str(client.client.base_url).startswith("https://api.minimaxi.com")


# ---------------------------------------------------------------------------
# Model constants
# ---------------------------------------------------------------------------

class TestModelConstants:
    def test_expected_models(self):
        assert "MiniMax-M2.7" in MINIMAX_MODELS
        assert "MiniMax-M2.7-highspeed" in MINIMAX_MODELS
        assert len(MINIMAX_MODELS) == 2


# ---------------------------------------------------------------------------
# process_llm_response
# ---------------------------------------------------------------------------

def _mock_response(finish_reason="stop", content="Hello!", tool_calls=None):
    """Build a mock OpenAI-style response."""
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls

    choice = MagicMock()
    choice.finish_reason = finish_reason
    choice.message = message

    response = MagicMock()
    response.choices = [choice]
    return response


class TestProcessLlmResponse:
    def test_stop_response(self, minimax_cfg):
        client = MiniMaxClient(minimax_cfg)
        resp = _mock_response(finish_reason="stop", content="Hello world")
        text, is_invalid, msg = client.process_llm_response(resp)
        assert text == "Hello world"
        assert is_invalid is False
        assert msg["role"] == "assistant"
        assert msg["content"] == "Hello world"

    def test_empty_response(self, minimax_cfg):
        client = MiniMaxClient(minimax_cfg)
        text, is_invalid, msg = client.process_llm_response(None)
        assert text == ""
        assert is_invalid is True
        assert msg == {}

    def test_empty_choices(self, minimax_cfg):
        client = MiniMaxClient(minimax_cfg)
        resp = MagicMock()
        resp.choices = []
        text, is_invalid, msg = client.process_llm_response(resp)
        assert is_invalid is True

    def test_tool_calls_response(self, minimax_cfg):
        client = MiniMaxClient(minimax_cfg)
        tc = MagicMock()
        tc.id = "call_123"
        tc.function.name = "search"
        tc.function.arguments = '{"q":"test"}'
        resp = _mock_response(finish_reason="tool_calls", content="", tool_calls=[tc])
        text, is_invalid, msg = client.process_llm_response(resp)
        assert is_invalid is False
        assert "tool_calls" in msg
        assert msg["tool_calls"][0]["id"] == "call_123"
        assert "search" in text

    def test_tool_calls_with_content(self, minimax_cfg):
        client = MiniMaxClient(minimax_cfg)
        tc = MagicMock()
        tc.id = "call_456"
        tc.function.name = "fetch"
        tc.function.arguments = "{}"
        resp = _mock_response(finish_reason="tool_calls", content="Thinking...", tool_calls=[tc])
        text, is_invalid, msg = client.process_llm_response(resp)
        assert text == "Thinking..."
        assert msg["content"] == "Thinking..."

    def test_length_response(self, minimax_cfg):
        client = MiniMaxClient(minimax_cfg)
        resp = _mock_response(finish_reason="length", content="partial")
        text, is_invalid, msg = client.process_llm_response(resp)
        assert text == "partial"
        assert is_invalid is False

    def test_length_empty_content(self, minimax_cfg):
        client = MiniMaxClient(minimax_cfg)
        resp = _mock_response(finish_reason="length", content="")
        text, _, _ = client.process_llm_response(resp)
        assert "thinking block" in text.lower() or "empty" in text.lower()

    def test_unsupported_finish_reason(self, minimax_cfg):
        client = MiniMaxClient(minimax_cfg)
        resp = _mock_response(finish_reason="content_filter", content="")
        with pytest.raises(ValueError, match="Unsupported finish reason"):
            client.process_llm_response(resp)


# ---------------------------------------------------------------------------
# extract_tool_calls_info
# ---------------------------------------------------------------------------

class TestExtractToolCalls:
    def test_no_tool_calls_on_stop(self, minimax_cfg):
        client = MiniMaxClient(minimax_cfg)
        resp = _mock_response(finish_reason="stop", content="Hi")
        ids, results = client.extract_tool_calls_info(resp, "Hi")
        assert ids == []
        assert results == []


# ---------------------------------------------------------------------------
# update_message_history
# ---------------------------------------------------------------------------

class TestUpdateMessageHistory:
    def test_appends_tool_results(self, minimax_cfg):
        client = MiniMaxClient(minimax_cfg)
        history = []
        tool_info = [("call_1", {"text": "result1"}), ("call_2", {"text": "result2"})]
        result = client.update_message_history(history, tool_info)
        assert len(result) == 2
        assert result[0]["role"] == "tool"
        assert result[0]["tool_call_id"] == "call_1"
        assert result[1]["content"] == "result2"


# ---------------------------------------------------------------------------
# _create_message (async)
# ---------------------------------------------------------------------------

class TestCreateMessage:
    @pytest.mark.asyncio
    async def test_injects_system_prompt(self, minimax_cfg):
        client = MiniMaxClient(minimax_cfg)
        mock_resp = _mock_response()
        client.client = AsyncMock()
        client.client.chat.completions.create = AsyncMock(return_value=mock_resp)

        messages = [{"role": "user", "content": "Hello"}]
        await client._create_message("You are helpful", messages, None)

        call_args = client.client.chat.completions.create.call_args
        sent_messages = call_args.kwargs["messages"]
        assert sent_messages[0]["role"] == "system"

    @pytest.mark.asyncio
    async def test_replaces_existing_system(self, minimax_cfg):
        client = MiniMaxClient(minimax_cfg)
        mock_resp = _mock_response()
        client.client = AsyncMock()
        client.client.chat.completions.create = AsyncMock(return_value=mock_resp)

        messages = [
            {"role": "system", "content": "old prompt"},
            {"role": "user", "content": "Hello"},
        ]
        await client._create_message("new prompt", messages, None)

        call_args = client.client.chat.completions.create.call_args
        sent_messages = call_args.kwargs["messages"]
        assert sent_messages[0]["content"][0]["text"] == "new prompt"

    @pytest.mark.asyncio
    async def test_temperature_clamped(self):
        cfg = _make_config(temperature=0.0)
        client = MiniMaxClient(cfg)
        mock_resp = _mock_response()
        client.client = AsyncMock()
        client.client.chat.completions.create = AsyncMock(return_value=mock_resp)

        await client._create_message("sys", [{"role": "user", "content": "Hi"}], None)

        call_args = client.client.chat.completions.create.call_args
        assert call_args.kwargs["temperature"] == MINIMAX_TEMP_MIN

    @pytest.mark.asyncio
    async def test_top_p_included_when_not_default(self):
        cfg = _make_config(top_p=0.8)
        client = MiniMaxClient(cfg)
        mock_resp = _mock_response()
        client.client = AsyncMock()
        client.client.chat.completions.create = AsyncMock(return_value=mock_resp)

        await client._create_message("sys", [{"role": "user", "content": "Hi"}], None)

        call_args = client.client.chat.completions.create.call_args
        assert call_args.kwargs["top_p"] == 0.8

    @pytest.mark.asyncio
    async def test_top_p_excluded_when_default(self):
        cfg = _make_config(top_p=1.0)
        client = MiniMaxClient(cfg)
        mock_resp = _mock_response()
        client.client = AsyncMock()
        client.client.chat.completions.create = AsyncMock(return_value=mock_resp)

        await client._create_message("sys", [{"role": "user", "content": "Hi"}], None)

        call_args = client.client.chat.completions.create.call_args
        assert "top_p" not in call_args.kwargs

    @pytest.mark.asyncio
    async def test_stream_false(self, minimax_cfg):
        client = MiniMaxClient(minimax_cfg)
        mock_resp = _mock_response()
        client.client = AsyncMock()
        client.client.chat.completions.create = AsyncMock(return_value=mock_resp)

        await client._create_message("sys", [{"role": "user", "content": "Hi"}], None)

        call_args = client.client.chat.completions.create.call_args
        assert call_args.kwargs["stream"] is False


# ---------------------------------------------------------------------------
# handle_max_turns_reached_summary_prompt
# ---------------------------------------------------------------------------

class TestMaxTurnsPrompt:
    def test_returns_prompt_unchanged(self, minimax_cfg):
        client = MiniMaxClient(minimax_cfg)
        assert client.handle_max_turns_reached_summary_prompt([], "summarize") == "summarize"


# ---------------------------------------------------------------------------
# Integration test (requires MINIMAX_API_KEY)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not os.environ.get("MINIMAX_API_KEY"),
    reason="MINIMAX_API_KEY not set - skipping integration test",
)
class TestMiniMaxIntegration:
    @pytest.mark.asyncio
    async def test_basic_chat(self):
        cfg = _make_config(
            api_key=os.environ["MINIMAX_API_KEY"],
            base_url=os.environ.get("MINIMAX_BASE_URL", "https://api.minimax.io/v1"),
            max_tokens=64,
        )
        client = MiniMaxClient(cfg)
        messages = [{"role": "user", "content": "Say exactly: integration test passed"}]
        resp = await client._create_message("You are helpful.", messages, None)
        text, is_invalid, _ = client.process_llm_response(resp)
        assert not is_invalid
        assert len(text) > 0

    @pytest.mark.asyncio
    async def test_highspeed_model(self):
        cfg = _make_config(
            api_key=os.environ["MINIMAX_API_KEY"],
            base_url=os.environ.get("MINIMAX_BASE_URL", "https://api.minimax.io/v1"),
            model_name="MiniMax-M2.7-highspeed",
            max_tokens=32,
        )
        client = MiniMaxClient(cfg)
        messages = [{"role": "user", "content": "Reply with the word: OK"}]
        resp = await client._create_message("Be brief.", messages, None)
        text, is_invalid, _ = client.process_llm_response(resp)
        assert not is_invalid
        assert len(text) > 0

    @pytest.mark.asyncio
    async def test_system_prompt_handled(self):
        cfg = _make_config(
            api_key=os.environ["MINIMAX_API_KEY"],
            base_url=os.environ.get("MINIMAX_BASE_URL", "https://api.minimax.io/v1"),
            max_tokens=256,
        )
        client = MiniMaxClient(cfg)
        messages = [{"role": "user", "content": "What is 2+2? Answer with just the number."}]
        resp = await client._create_message(
            "You are a math tutor. Always answer with just the number.", messages, None
        )
        text, is_invalid, _ = client.process_llm_response(resp)
        assert not is_invalid
        assert len(text) > 0
