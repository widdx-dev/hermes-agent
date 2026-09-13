import pytest

from neural.events import NeuralEvent
from neural.integration import (
    NeuralRuntimeBridge,
    bind_runtime_bridge,
    current_runtime_bridge,
    reset_runtime_bridge,
)
from neural.runtime import NeuralRuntime


def test_bridge_senses_conversation_and_task_without_execution():
    runtime = NeuralRuntime()
    received: list[NeuralEvent] = []
    runtime.bus.subscribe("conversation.observed", received.append)
    runtime.bus.subscribe("task.observed", received.append)
    bridge = NeuralRuntimeBridge(runtime)

    conversation = bridge.observe_conversation("hello", correlation_id="turn-1")
    task = bridge.observe_task("task-7", correlation_id="turn-1")

    assert [event.event_type for event in received] == [
        "conversation.observed",
        "task.observed",
    ]
    assert conversation.payload == {"text": "hello", "length": 5}
    assert task.payload == {"task_id": "task-7"}


def test_bridge_observes_tool_and_error_as_advisory_events():
    runtime = NeuralRuntime()
    received: list[NeuralEvent] = []
    runtime.bus.subscribe("terminal.observed", received.append)
    runtime.bus.subscribe("error.observed", received.append)
    bridge = NeuralRuntimeBridge(runtime)

    bridge.observe_tool(
        "terminal",
        {"command": "pwd"},
        "{\"output\": \"/workspace\"}",
        duration_ms=12,
        correlation_id="turn-2",
    )
    bridge.observe_error("RuntimeError", "boom", correlation_id="turn-2")

    assert received[0].payload["tool_name"] == "terminal"
    assert received[0].payload["duration_ms"] == 12
    assert received[1].payload == {"error_type": "RuntimeError", "message": "boom"}


def test_bridge_environment_snapshot_contains_no_environment_values():
    runtime = NeuralRuntime()
    bridge = NeuralRuntimeBridge(runtime)

    event = bridge.observe_environment(
        cwd="/workspace",
        platform="linux",
        python_version="3.13",
        environment_keys=["OPENAI_API_KEY", "PATH"],
    )

    assert event.payload == {
        "cwd": "/workspace",
        "platform": "linux",
        "python_version": "3.13",
        "environment_key_count": 2,
    }
    assert "OPENAI_API_KEY" not in event.payload


def test_runtime_bridge_context_is_scoped_and_resettable():
    runtime = NeuralRuntime()
    bridge = NeuralRuntimeBridge(runtime)
    assert current_runtime_bridge() is None

    token = bind_runtime_bridge(bridge)
    try:
        assert current_runtime_bridge() is bridge
    finally:
        reset_runtime_bridge(token)

    assert current_runtime_bridge() is None


def test_bridge_never_executes_tools(monkeypatch: pytest.MonkeyPatch):
    runtime = NeuralRuntime()
    bridge = NeuralRuntimeBridge(runtime)

    def fail(*_args, **_kwargs):
        raise AssertionError("neural bridge must not execute tools")

    monkeypatch.setattr(runtime, "process", fail)
    event = bridge.observe_conversation("hello")

    assert event.event_type == "conversation.observed"
