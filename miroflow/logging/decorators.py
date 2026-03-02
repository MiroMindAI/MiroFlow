# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import contextvars
import inspect
from functools import wraps
from typing import Any, Callable, Dict, Optional

from .span import Span, new_id
from miroflow.logging.task_tracer import get_tracer, get_current_task_context_var

# ---- contextvars ----
CURRENT_SPAN_ID: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "CURRENT_SPAN_ID", default=None
)
CURRENT_SPAN_PATH: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "CURRENT_SPAN_PATH", default=None
)


def _default_span_name(func: Callable[..., Any], args: tuple[Any, ...]) -> str:
    if args and hasattr(args[0], "__class__"):
        module_name = getattr(args[0], "name", "")
        return f"{args[0].__class__.__name__}({module_name}).{func.__name__}"
    return f"{func.__module__}.{func.__name__}"


def span(
    name: Optional[str] = None,
    *,
    name_fn: Optional[
        Callable[[Callable[..., Any], tuple[Any, ...], Dict[str, Any]], str]
    ] = None,
    # Optional: allow caller to explicitly pass node_id/step_id (for heartbeat and step_logs)
    node_id_fn: Optional[
        Callable[[Callable[..., Any], tuple[Any, ...], Dict[str, Any]], Optional[str]]
    ] = None,
    step_id_fn: Optional[
        Callable[[Callable[..., Any], tuple[Any, ...], Dict[str, Any]], Optional[int]]
    ] = None,
):
    """
    Async decorator that:
      - creates Span with parent_span_id from CURRENT_SPAN_ID
      - appends span_start/span_end into tracer.data.step_logs
      - updates tracer.data.heartbeat.current_span = {...} on start, clears on end
      - maintains CURRENT_SPAN_ID to form a call tree
    """

    def decorator(func: Callable[..., Any]):
        if not inspect.iscoroutinefunction(func):
            raise TypeError("@span can only decorate async functions")

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any):
            tracer = get_tracer()

            # span name
            if name_fn is not None:
                span_name = name_fn(func, args, kwargs)
            elif name is not None:
                span_name = name
            else:
                span_name = _default_span_name(func, args)

            # trace/run ids stable in a task
            task_context_var = get_current_task_context_var()

            if task_context_var is None:
                return await func(*args, **kwargs)

            parent_span_id = CURRENT_SPAN_ID.get()
            span_id = new_id("sp_")

            # path
            parent_path = CURRENT_SPAN_PATH.get()
            if parent_path:
                span_path = f"{parent_path}->{span_name}"
            else:
                span_path = span_name

            path_token = CURRENT_SPAN_PATH.set(span_path)

            # compute node_id/step_id (optional)
            node_id = node_id_fn(func, args, kwargs) if node_id_fn else None
            step_id = step_id_fn(func, args, kwargs) if step_id_fn else None

            sp = Span(
                task_id=task_context_var.task_id,
                attempt_id=task_context_var.attempt_id,
                retry_id=task_context_var.retry_id,
                span_id=span_id,
                parent_span_id=parent_span_id,
                name=span_name,
            )
            # Store additional metadata in attrs
            if span_path:
                sp.attrs["path"] = span_path
            if node_id:
                sp.attrs["node_id"] = node_id
            if step_id is not None:
                sp.attrs["step_id"] = step_id

            # update heartbeat current_span (latest-only)
            if tracer is not None:
                tracer.set_current_span(sp)

                tracer.append_step_event(
                    {
                        "type": "span_start",
                        # "run_id": run_id,
                        "span_id": span_id,
                        "parent_span_id": parent_span_id,
                        "path": span_path,
                        # "node_id": node_id,
                        # "step_id": step_id,
                        "start_ts": sp.start_ts,
                    }
                )

            span_token = CURRENT_SPAN_ID.set(span_id)

            try:
                result = await func(*args, **kwargs)
                sp.status = "ok"
                return result
            except Exception as e:
                sp.status = "error"
                sp.error = {"type": type(e).__name__, "message": str(e)}
                raise
            finally:
                sp.end()
                if tracer is not None:
                    event = {
                        "type": "span_end",
                        # "run_id": run_id,
                        "span_id": span_id,
                        "parent_span_id": parent_span_id,
                        "path": span_path,
                        # "node_id": node_id,
                        # "step_id": step_id,
                        # "start_ts": sp.start_ts,
                        "end_ts": sp.end_ts,
                        "duration_ms": sp.duration_ms,
                        # "status": sp.status,
                        # "error": sp.error,
                    }
                    if sp.error:
                        event["error"] = sp.error
                    tracer.append_step_event(event)
                    tracer.set_current_span(None)

                CURRENT_SPAN_ID.reset(span_token)
                if path_token is not None:
                    CURRENT_SPAN_PATH.reset(path_token)

        return wrapper

    return decorator


# compatibility name
def span_decorator(*args, **kwargs):
    return span(*args, **kwargs)
