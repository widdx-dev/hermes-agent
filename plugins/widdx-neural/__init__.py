"""WIDDX neural lifecycle observers.

This plugin is intentionally observer-only. It converts existing Hermes lifecycle
signals into NeuralEvents and never blocks, approves, dispatches, or modifies tools.
"""

from __future__ import annotations

import os
import platform as platform_module
import sys
import threading
from typing import Any

from neural.integration import NeuralRuntimeBridge


_LOCK = threading.RLock()
_BRIDGES: dict[str, NeuralRuntimeBridge] = {}
_MAX_SESSIONS = 256


def _bridge(session_id: str) -> NeuralRuntimeBridge:
    key = session_id or "anonymous"
    with _LOCK:
        bridge = _BRIDGES.get(key)
        if bridge is None:
            bridge = NeuralRuntimeBridge()
            _BRIDGES[key] = bridge
            if len(_BRIDGES) > _MAX_SESSIONS:
                oldest = next(iter(_BRIDGES))
                if oldest != key:
                    _BRIDGES.pop(oldest, None)
        return bridge


def _observe_environment(bridge: NeuralRuntimeBridge, *, correlation_id: str | None = None) -> None:
    try:
        bridge.observe_environment(
            cwd=os.getcwd(),
            platform=platform_module.system().lower(),
            python_version=platform_module.python_version(),
            environment_keys=list(os.environ),
            correlation_id=correlation_id,
        )
    except Exception:
        return


def _on_session_start(session_id: str = "", **kwargs: Any) -> None:
    bridge = _bridge(session_id)
    _observe_environment(bridge, correlation_id=kwargs.get("turn_id"))


def _pre_llm_call(
    session_id: str = "",
    user_message: Any = "",
    task_id: str = "",
    turn_id: str = "",
    **kwargs: Any,
) -> None:
    bridge = _bridge(session_id)
    text = user_message if isinstance(user_message, str) else str(user_message)
    bridge.observe_conversation(text, correlation_id=turn_id or task_id or None)
    if task_id:
        bridge.observe_task(task_id, correlation_id=turn_id or None)


def _post_tool_call(
    tool_name: str = "",
    args: dict | None = None,
    result: str = "",
    task_id: str = "",
    session_id: str = "",
    turn_id: str = "",
    duration_ms: int = 0,
    status: str = "",
    error_type: str = "",
    error_message: str = "",
    **kwargs: Any,
) -> None:
    bridge = _bridge(session_id)
    bridge.observe_tool(
        tool_name,
        args or {},
        result,
        duration_ms=duration_ms,
        correlation_id=turn_id or task_id or None,
    )
    if status == "error" or error_type or error_message:
        bridge.observe_error(
            error_type or "ToolError",
            error_message or result,
            correlation_id=turn_id or task_id or None,
        )


def _post_llm_call(
    session_id: str = "",
    assistant_response: str = "",
    turn_id: str = "",
    **kwargs: Any,
) -> None:
    # Keep the first version deliberately narrow: the conversation cell observes
    # inbound conversation, while model output remains available through the
    # existing Hermes transcript for future prediction/learning work.
    _bridge(session_id)


def _on_session_end(session_id: str = "", **kwargs: Any) -> None:
    with _LOCK:
        _BRIDGES.pop(session_id or "anonymous", None)


def register(ctx: Any) -> None:
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("pre_llm_call", _pre_llm_call)
    ctx.register_hook("post_tool_call", _post_tool_call)
    ctx.register_hook("post_llm_call", _post_llm_call)
    ctx.register_hook("on_session_end", _on_session_end)


__all__ = ["register"]
