import pytest

from neural.events import NeuralEvent, NeuralSignal
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

    terminal = bridge.observe_tool(
        "terminal",
        {"command": "pwd"},
        "{\"output\": \"/workspace\"}",
        duration_ms=12,
        correlation_id="turn-2",
    )
    error = bridge.observe_error("RuntimeError", "boom", correlation_id="turn-2")

    assert received[0].payload["tool_name"] == "terminal"
    assert received[0].payload["duration_ms"] == 12
    assert received[1].payload == {"error_type": "RuntimeError", "message": "boom"}
    assert terminal is received[0]
    assert error is received[1]


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
    bridge = NeuralRuntimeBridge()

    def fail(*_args, **_kwargs):
        raise AssertionError("neural bridge must not execute tools")

    monkeypatch.setattr(NeuralRuntime, "process", fail)
    event = bridge.observe_conversation("hello")

    assert event.event_type == "conversation.observed"


def test_process_event_processes_existing_eligible_event_without_resensing():
    runtime = NeuralRuntime()
    bridge = NeuralRuntimeBridge(runtime)
    event = bridge.observe_conversation("hello", correlation_id="turn-3")
    processed: list[tuple[NeuralEvent, bool]] = []
    signal = NeuralSignal(source="test", target="memory", value=0.5)

    def process(observed: NeuralEvent, *, reinforce: bool = False, success: bool = True):
        processed.append((observed, reinforce))
        return [signal]

    runtime.process = process  # type: ignore[method-assign]

    result = bridge.process_event(event)

    assert result == [signal]
    assert processed == [(event, False)]


def test_process_event_processes_all_eligible_event_types():
    bridge = NeuralRuntimeBridge()
    processed: list[str] = []

    def process(event: NeuralEvent, *, reinforce: bool = False, success: bool = True):
        processed.append(event.event_type)
        return []

    bridge.runtime.process = process  # type: ignore[method-assign]
    events = [
        NeuralEvent(source="test", event_type=event_type)
        for event_type in (
            "conversation.observed",
            "task.observed",
            "terminal.observed",
            "error.observed",
        )
    ]

    for event in events:
        assert bridge.process_event(event) == []

    assert processed == [event.event_type for event in events]


def test_process_event_allows_environment_only_when_explicitly_requested():
    bridge = NeuralRuntimeBridge()
    event = NeuralEvent(source="test", event_type="environment.observed")
    processed: list[NeuralEvent] = []
    bridge.runtime.process = lambda event, **_: processed.append(event) or []  # type: ignore[method-assign]

    assert bridge.process_event(event) == []
    assert processed == []
    assert bridge.process_event(event, allow_environment=True) == []
    assert processed == [event]


def test_process_event_ignores_unsupported_event_types():
    bridge = NeuralRuntimeBridge()
    event = NeuralEvent(source="test", event_type="unknown.observed")
    bridge.runtime.process = lambda *_args, **_kwargs: pytest.fail("unsupported event was processed")  # type: ignore[method-assign]

    assert bridge.process_event(event) == []


def test_process_event_is_fail_open_and_never_reinforces():
    bridge = NeuralRuntimeBridge()
    event = NeuralEvent(source="test", event_type="error.observed")
    calls: list[tuple[NeuralEvent, bool]] = []

    def fail(event: NeuralEvent, *, reinforce: bool = False, success: bool = True):
        calls.append((event, reinforce))
        raise RuntimeError("processor failure")

    bridge.runtime.process = fail  # type: ignore[method-assign]

    assert bridge.process_event(event) == []
    assert calls == [(event, False)]
