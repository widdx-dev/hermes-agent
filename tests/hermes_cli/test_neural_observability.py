from neural.events import NeuralEvent
from hermes_cli import observability
from hermes_cli.observability import neural


def test_lifecycle_observer_forwards_events_to_neural_runtime(monkeypatch):
    received: list[NeuralEvent] = []

    def fake_observe(hook_name, **kwargs):
        received.append(NeuralEvent("test", f"{hook_name}.observed", kwargs))

    monkeypatch.setattr("hermes_cli.observability.neural.observe_lifecycle", fake_observe)

    observability.observe_lifecycle(
        "on_session_start",
        session_id="session-1",
        turn_id="turn-1",
    )

    assert [event.event_type for event in received] == ["on_session_start.observed"]
    assert received[0].payload == {
        "session_id": "session-1",
        "turn_id": "turn-1",
    }


def test_neural_observer_advertises_its_supported_hooks():
    assert neural.handles_hook("on_session_start")
    assert neural.handles_hook("pre_llm_call")
    assert neural.handles_hook("post_tool_call")
    assert neural.handles_hook("on_session_end")
    assert not neural.handles_hook("post_llm_call")


def test_neural_observer_maps_core_lifecycle_events(monkeypatch):
    calls = []
    events = {}

    class FakeBridge:
        def _event(self, event_type):
            event = NeuralEvent("test", event_type)
            events[event_type] = event
            return event

        def observe_environment(self, **kwargs):
            calls.append(("environment", kwargs))
            return self._event("environment.observed")

        def observe_conversation(self, text, **kwargs):
            calls.append(("conversation", text, kwargs))
            return self._event("conversation.observed")

        def observe_task(self, task_id, **kwargs):
            calls.append(("task", task_id, kwargs))
            return self._event("task.observed")

        def observe_tool(self, tool_name, args, result, **kwargs):
            calls.append(("tool", tool_name, args, result, kwargs))
            return self._event("terminal.observed")

        def observe_error(self, error_type, message, **kwargs):
            calls.append(("error", error_type, message, kwargs))
            return self._event("error.observed")

        def process_event(self, event, **kwargs):
            calls.append(("process", event, kwargs))
            return []

    monkeypatch.setattr(neural, "_BRIDGES", {})
    monkeypatch.setattr(neural, "NeuralRuntimeBridge", FakeBridge)

    neural.observe_lifecycle(
        "on_session_start",
        session_id="session-1",
        cwd="/workspace",
        platform="linux",
        python_version="3.13",
        environment_keys=["PATH"],
    )
    neural.observe_lifecycle(
        "pre_llm_call",
        session_id="session-1",
        task_id="task-1",
        turn_id="turn-1",
        user_message="hello",
    )
    neural.observe_lifecycle(
        "post_tool_call",
        session_id="session-1",
        task_id="task-1",
        turn_id="turn-1",
        tool_name="terminal",
        args={"command": "pwd"},
        result="/workspace",
        duration_ms=5,
        status="error",
        error_type="RuntimeError",
        error_message="boom",
    )

    assert [call[0] for call in calls] == [
        "environment",
        "process",
        "conversation",
        "process",
        "task",
        "process",
        "tool",
        "process",
        "error",
        "process",
    ]
    assert calls[1][1] is events["environment.observed"]
    assert calls[2][1] == "hello"
    assert calls[3][1] is events["conversation.observed"]
    assert calls[4][1] == "task-1"
    assert calls[5][1] is events["task.observed"]
    assert calls[6][1:] == (
        "terminal",
        {"command": "pwd"},
        "/workspace",
        {"duration_ms": 5, "correlation_id": "turn-1"},
    )
    assert calls[7][1] is events["terminal.observed"]
    assert calls[8][1:] == (
        "RuntimeError",
        "boom",
        {"correlation_id": "turn-1"},
    )
    assert calls[9][1] is events["error.observed"]


def test_neural_observer_does_not_process_missing_observations(monkeypatch):
    class FakeBridge:
        def observe_conversation(self, **kwargs):
            return None

        def process_event(self, *_args, **_kwargs):
            raise AssertionError("missing observation must not be processed")

    monkeypatch.setattr(neural, "_BRIDGES", {})
    monkeypatch.setattr(neural, "NeuralRuntimeBridge", FakeBridge)

    neural.observe_lifecycle(
        "pre_llm_call",
        session_id="session-1",
        user_message="hello",
    )


def test_neural_observer_cleans_session_bridge(monkeypatch):
    bridge = object()
    monkeypatch.setattr(neural, "_BRIDGES", {"session-1": bridge})

    neural.observe_lifecycle("on_session_end", session_id="session-1")

    assert neural._BRIDGES == {}


def test_neural_observer_is_best_effort(monkeypatch):
    def fail(*_args, **_kwargs):
        raise RuntimeError("neural failure")

    monkeypatch.setattr("hermes_cli.observability.neural.observe_lifecycle", fail)

    observability.observe_lifecycle("post_tool_call", tool_name="terminal")
