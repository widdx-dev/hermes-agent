"""Always-on, execution-free neural observation for Hermes lifecycle events."""

from __future__ import annotations

import os
import platform as platform_module
import threading
from typing import Any, Mapping

from neural.events import NeuralEvent
from neural.integration import NeuralRuntimeBridge

_LOCK = threading.RLock()
_BRIDGES: dict[str, NeuralRuntimeBridge] = {}
_SUPPORTED_HOOKS = frozenset({
    "on_session_start",
    "pre_llm_call",
    "post_tool_call",
    "on_session_end",
})


def handles_hook(hook_name: str) -> bool:
    return hook_name in _SUPPORTED_HOOKS


def _bridge(session_id: str) -> NeuralRuntimeBridge:
    key = session_id or "anonymous"
    with _LOCK:
        bridge = _BRIDGES.get(key)
        if bridge is None:
            bridge = NeuralRuntimeBridge()
            _BRIDGES[key] = bridge
        return bridge


def _process(bridge: NeuralRuntimeBridge, event: NeuralEvent | None, *, allow_environment: bool = False) -> None:
    if event is None:
        return
    try:
        bridge.process_event(event, allow_environment=allow_environment)
    except Exception:
        # Processing is advisory and must never become an agent failure path.
        return


def observe_lifecycle(hook_name: str, **kwargs: Any) -> None:
    """Forward supported Hermes lifecycle facts into neural perception and processing.

    This observer is advisory and fail-open. It never dispatches tools, invokes a
    model, changes approval/security state, or performs network I/O.
    """
    session_id = str(kwargs.get("session_id") or "")

    if hook_name == "on_session_start":
        bridge = _bridge(session_id)
        event = bridge.observe_environment(
            cwd=str(kwargs.get("cwd") or os.getcwd()),
            platform=str(kwargs.get("platform") or platform_module.system().lower()),
            python_version=str(kwargs.get("python_version") or platform_module.python_version()),
            environment_keys=list(kwargs.get("environment_keys") or os.environ.keys()),
            correlation_id=str(kwargs.get("turn_id") or "") or None,
        )
        _process(bridge, event, allow_environment=True)
        return

    if hook_name == "pre_llm_call":
        bridge = _bridge(session_id)
        user_message = kwargs.get("user_message", "")
        text = user_message if isinstance(user_message, str) else str(user_message)
        correlation_id = str(kwargs.get("turn_id") or kwargs.get("task_id") or "") or None
        _process(
            bridge,
            bridge.observe_conversation(text, correlation_id=correlation_id),
        )
        task_id = str(kwargs.get("task_id") or "")
        if task_id:
            _process(
                bridge,
                bridge.observe_task(task_id, correlation_id=correlation_id),
            )
        return

    if hook_name == "post_tool_call":
        bridge = _bridge(session_id)
        args = kwargs.get("args")
        if not isinstance(args, Mapping):
            args = {}
        tool_name = str(kwargs.get("tool_name") or "")
        result = kwargs.get("result", "")
        result_text = result if isinstance(result, str) else str(result)
        correlation_id = str(kwargs.get("turn_id") or kwargs.get("task_id") or "") or None
        _process(
            bridge,
            bridge.observe_tool(
                tool_name,
                args,
                result_text,
                duration_ms=int(kwargs.get("duration_ms") or 0),
                correlation_id=correlation_id,
            ),
        )
        error_type = str(kwargs.get("error_type") or "")
        error_message = str(kwargs.get("error_message") or "")
        status = str(kwargs.get("status") or "")
        if status == "error" or error_type or error_message:
            _process(
                bridge,
                bridge.observe_error(
                    error_type or "ToolError",
                    error_message or result_text,
                    correlation_id=correlation_id,
                ),
            )
        return

    if hook_name == "on_session_end":
        with _LOCK:
            _BRIDGES.pop(session_id or "anonymous", None)
