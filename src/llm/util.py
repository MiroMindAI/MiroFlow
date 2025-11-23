# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import functools
import time
from typing import Awaitable, Callable, Optional, TypeVar, AsyncIterator, Any
import uuid
from openai.types.chat import ChatCompletion

T = TypeVar("T")


def with_timeout(
    timeout_s: float = 300.0,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """
    Decorator: wraps any *async* function in asyncio.wait_for().
    Usage:
        @with_timeout(20)
        async def create_message_foo(...): ...
    """

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_s)

        return wrapper

    return decorator


async def collect_openai_stream(stream: AsyncIterator[Any], stream_message_callback: Optional[Callable] = None) -> Any:
    """
    Collect all chunks from an OpenAI streaming response and merge them into a single response object.

    :param stream: AsyncIterator of streaming chunks from OpenAI API
    :param stream_message_callback: Optional callback for streaming output. 
                                   Signature: async def callback(content: str, is_final: bool) -> bool
    :return: Complete response object (similar to non-streaming response)
    """
    collected_content = ""
    collected_tool_calls = []
    first_chunk = None
    finish_reason = None
    usage_data = None
    msg_id = str(uuid.uuid4())
    
    # Streaming buffer variables
    emit_message_flag = True
    buffer = ""  # 用于缓存内容的缓冲区
    last_emit_time = time.time()  # 记录上次发送消息的时间
    buffer_interval = 0.1  # 100ms 间隔

    async for chunk in stream:
        if first_chunk is None:
            first_chunk = chunk

        # Collect usage data if present
        if hasattr(chunk, "usage") and chunk.usage:
            usage_data = chunk.usage

        # Merge chunk data
        if hasattr(chunk, "choices") and len(chunk.choices) > 0:
            delta = chunk.choices[0].delta

            # Accumulate content
            if hasattr(delta, "content") and delta.content:
                collected_content += delta.content
                
                # Handle streaming output if callback is provided
                if stream_message_callback is not None:
                    buffer += delta.content
                    current_time = time.time()
                    # 检查是否达到时间间隔且缓冲区有内容
                    if current_time - last_emit_time >= buffer_interval and buffer and emit_message_flag:
                        emit_message_flag = await stream_message_callback(msg_id,buffer, False)
                        buffer = ""  # 清空缓冲区
                        last_emit_time = current_time  # 更新上次发送时间

            # Accumulate tool calls
            if hasattr(delta, "tool_calls") and delta.tool_calls:
                for tool_call_delta in delta.tool_calls:
                    # Ensure we have enough tool call slots
                    while len(collected_tool_calls) <= tool_call_delta.index:
                        collected_tool_calls.append({
                            "id": "",
                            "type": "function",
                            "function": {
                                "name": "",
                                "arguments": ""
                            }
                        })

                    tool_call = collected_tool_calls[tool_call_delta.index]

                    if hasattr(tool_call_delta, "id") and tool_call_delta.id:
                        tool_call["id"] = tool_call_delta.id

                    if hasattr(tool_call_delta, "function"):
                        if hasattr(tool_call_delta.function, "name") and tool_call_delta.function.name:
                            tool_call["function"]["name"] = tool_call_delta.function.name
                        if hasattr(tool_call_delta.function, "arguments") and tool_call_delta.function.arguments:
                            tool_call["function"]["arguments"] += tool_call_delta.function.arguments

            # Update finish reason
            if hasattr(chunk.choices[0], "finish_reason") and chunk.choices[0].finish_reason:
                finish_reason = chunk.choices[0].finish_reason
    
    # 处理剩余的缓冲区内容
    if stream_message_callback is not None:
        if buffer and emit_message_flag:
            emit_message_flag = await stream_message_callback(msg_id, buffer, False)
        # 发送最终完成信号
        await stream_message_callback(msg_id, "", True)

    # Build final response object using the OpenAI response model
    if first_chunk is None:
        raise ValueError("Stream was empty")

    # Create response structure
    response_dict = {
        "id": first_chunk.id,
        "model": first_chunk.model,
        "created": first_chunk.created,
        "object": "chat.completion",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": collected_content or None,
            },
            "finish_reason": finish_reason
        }]
    }

    # Add tool_calls if present
    if collected_tool_calls:
        response_dict["choices"][0]["message"]["tool_calls"] = collected_tool_calls

    # Add usage data if present
    if usage_data:
        response_dict["usage"] = {
            "prompt_tokens": getattr(usage_data, "prompt_tokens", 0),
            "completion_tokens": getattr(usage_data, "completion_tokens", 0),
            "total_tokens": getattr(usage_data, "total_tokens", 0),
        }

    # Use ChatCompletion (non-streaming response type)
    final_response = ChatCompletion.model_validate(response_dict)

    return final_response


async def collect_anthropic_stream(stream: AsyncIterator[Any]) -> Any:
    """
    Collect all chunks from an Anthropic streaming response and merge them into a single response object.

    :param stream: AsyncIterator of streaming chunks from Anthropic API
    :return: Complete response object (similar to non-streaming response)
    """
    import json

    final_response = None
    current_content_blocks = []
    content_block_metadata = []  # Store metadata like id, name for tool_use blocks

    async for chunk in stream:
        # Handle different event types
        if hasattr(chunk, "type"):
            if chunk.type == "message_start":
                # Initialize response from message_start event
                final_response = chunk.message

            elif chunk.type == "content_block_start":
                # Start a new content block
                if hasattr(chunk, "content_block"):
                    content_block = chunk.content_block
                    # Store the initial block structure
                    if content_block.type == "text":
                        current_content_blocks.append({"type": "text", "text": ""})
                        content_block_metadata.append({})
                    elif content_block.type == "tool_use":
                        current_content_blocks.append({
                            "type": "tool_use",
                            "input": ""
                        })
                        # Store tool_use metadata
                        content_block_metadata.append({
                            "id": content_block.id,
                            "name": content_block.name
                        })

            elif chunk.type == "content_block_delta":
                # Update content block with delta
                if hasattr(chunk, "delta"):
                    delta = chunk.delta
                    index = chunk.index

                    # Ensure we have a content block at this index
                    while len(current_content_blocks) <= index:
                        current_content_blocks.append({"type": "text", "text": ""})
                        content_block_metadata.append({})

                    if delta.type == "text_delta":
                        if current_content_blocks[index]["type"] == "text":
                            current_content_blocks[index]["text"] += delta.text
                    elif delta.type == "input_json_delta":
                        # Accumulate JSON input for tool_use
                        current_content_blocks[index]["input"] += delta.partial_json

            elif chunk.type == "content_block_stop":
                # Content block is complete
                pass

            elif chunk.type == "message_delta":
                # Update message-level fields
                if hasattr(chunk, "delta"):
                    if hasattr(chunk.delta, "stop_reason"):
                        final_response.stop_reason = chunk.delta.stop_reason

            elif chunk.type == "message_stop":
                # Message is complete
                pass

    # Post-process content blocks to add metadata and parse JSON inputs
    for i, block in enumerate(current_content_blocks):
        if block["type"] == "tool_use":
            # Add stored metadata
            if i < len(content_block_metadata):
                block.update(content_block_metadata[i])
            # Parse accumulated JSON string to dict
            if "input" in block and isinstance(block["input"], str):
                try:
                    block["input"] = json.loads(block["input"])
                except json.JSONDecodeError:
                    # Keep as string if parsing fails
                    pass

    # Convert dict content blocks to proper Anthropic content block objects
    # We need to reconstruct them using the proper model classes
    if final_response and current_content_blocks:
        # Import Anthropic types
        from anthropic.types import TextBlock, ToolUseBlock

        typed_content_blocks = []
        for block in current_content_blocks:
            if block["type"] == "text":
                typed_content_blocks.append(TextBlock(type="text", text=block["text"]))
            elif block["type"] == "tool_use":
                typed_content_blocks.append(ToolUseBlock(
                    type="tool_use",
                    id=block.get("id", ""),
                    name=block.get("name", ""),
                    input=block.get("input", {})
                ))

        final_response.content = typed_content_blocks

    return final_response
