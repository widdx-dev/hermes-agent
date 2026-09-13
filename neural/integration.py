"""Execution-free bridge from Hermes runtime lifecycle events into neural perception."""

from __future__ import annotations

import contextvars
from typing import Any, Mapping

from neural.events import NeuralEvent, NeuralSignal
from neural.perception import ConversationCell, EnvironmentCell, ErrorCell, TaskCell, TerminalCell
from neural.runtime import NeuralRuntime


_CURRENT_BRIDGE: contextvars.ContextVar[NeuralRuntimeBridge | None] = contextvars.ContextVar(
    "neural_runtime_bridge", default=None
)
_ELIGIBLE_EVENT_TYPES = frozenset(
    {
        "conversation.observed",
        "task.observed",
        "terminal.observed",
        "error.observed",
    }
)


class NeuralRuntimeBridge:
    """Translate Hermes lifecycle facts into advisory neural observations.

    The bridge deliberately calls only ``NeuralRuntime.sense`` while observing and
    ``NeuralRuntime.process`` at an explicit processing boundary. It never dispatches
    tools, changes policy, invokes a model, touches credentials, or performs I/O.
    """

    def __init__(self, runtime: NeuralRuntime | None = None) -> None:
        self.runtime = runtime or NeuralRuntime()
        self.conversation = ConversationCell()
        self.task = TaskCell()
        self.terminal = TerminalCell()
        self.error = ErrorCell()
        self.environment = EnvironmentCell()

    def _sense(
        self,
        cell: Any,
        payload: Mapping[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> NeuralEvent | None:
        try:
            return self.runtime.sense(cell, payload, correlation_id=correlation_id)
        except Exception:
            # Neural observation is best-effort and must never become an agent failure path.
            return None

    def observe_conversation(
        self, text: str, *, correlation_id: str | None = None
    ) -> NeuralEvent | None:
        return self._sense(
            self.conversation,
            {"text": text, "length": len(text)},
            correlation_id=correlation_id,
        )

    def observe_task(
        self, task_id: str, *, correlation_id: str | None = None
    ) -> NeuralEvent | None:
        return self._sense(self.task, {"task_id": task_id}, correlation_id=correlation_id)

    def observe_tool(
        self,
        tool_name: str,
        args: Mapping[str, Any],
        result: str,
        *,
        duration_ms: int,
        correlation_id: str | None = None,
    ) -> NeuralEvent | None:
        if tool_name != "terminal":
            return None
        return self._sense(
            self.terminal,
            {
                "tool_name": tool_name,
                "args": dict(args),
                "result": result,
                "duration_ms": duration_ms,
            },
            correlation_id=correlation_id,
        )

    def observe_error(
        self,
        error_type: str,
        message: str,
        *,
        correlation_id: str | None = None,
    ) -> NeuralEvent | None:
        return self._sense(
            self.error,
            {"error_type": error_type, "message": message},
            correlation_id=correlation_id,
        )

    def observe_environment(
        self,
        *,
        cwd: str,
        platform: str,
        python_version: str,
        environment_keys: list[str],
        correlation_id: str | None = None,
    ) -> NeuralEvent | None:
        return self._sense(
            self.environment,
            {
                "cwd": cwd,
                "platform": platform,
                "python_version": python_version,
                "environment_key_count": len(environment_keys),
            },
            correlation_id=correlation_id,
        )

    def process_event(
        self,
        event: NeuralEvent,
        *,
        allow_environment: bool = False,
    ) -> list[NeuralSignal]:
        """Process one existing observation at an explicit advisory boundary.

        The event is never re-sensed or sent back through the Hermes lifecycle. Only
        allowlisted observation types reach the advisory processor, and processing is
        fail-open with reinforcement disabled.
        """
        if event.event_type not in _ELIGIBLE_EVENT_TYPES:
            if not (allow_environment and event.event_type == "environment.observed"):
                return []
        try:
            return self.runtime.process(event, reinforce=False)
        except Exception:
            # Processor failures must never affect Hermes execution or approval paths.
            return []


def bind_runtime_bridge(bridge: NeuralRuntimeBridge) -> contextvars.Token[NeuralRuntimeBridge | None]:
    """Bind the bridge to the current agent execution context."""
    return _CURRENT_BRIDGE.set(bridge)


def current_runtime_bridge() -> NeuralRuntimeBridge | None:
    return _CURRENT_BRIDGE.get()


def reset_runtime_bridge(token: contextvars.Token[NeuralRuntimeBridge | None]) -> None:
    _CURRENT_BRIDGE.reset(token)


__all__ = [
    "NeuralRuntimeBridge",
    "bind_runtime_bridge",
    "current_runtime_bridge",
    "reset_runtime_bridge",
]
