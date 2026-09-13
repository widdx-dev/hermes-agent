from neural.events import NeuralEvent
from hermes_cli import observability


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


def test_neural_observer_is_best_effort(monkeypatch):
    def fail(*_args, **_kwargs):
        raise RuntimeError("neural failure")

    monkeypatch.setattr("hermes_cli.observability.neural.observe_lifecycle", fail)

    observability.observe_lifecycle("post_tool_call", tool_name="terminal")
