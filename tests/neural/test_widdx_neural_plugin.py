import importlib.util
from pathlib import Path

from neural.events import NeuralEvent


PLUGIN = Path(__file__).parents[2] / "plugins" / "widdx-neural" / "__init__.py"


def _load_plugin():
    spec = importlib.util.spec_from_file_location("widdx_neural_plugin", PLUGIN)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class HookContext:
    def __init__(self):
        self.hooks = {}

    def register_hook(self, name, callback):
        self.hooks[name] = callback


def test_plugin_registers_only_observer_hooks():
    plugin = _load_plugin()
    ctx = HookContext()

    plugin.register(ctx)

    assert set(ctx.hooks) == {
        "on_session_start",
        "pre_llm_call",
        "post_tool_call",
        "post_llm_call",
        "on_session_end",
    }


def test_plugin_lifecycle_emits_neural_events_without_tool_execution(monkeypatch):
    plugin = _load_plugin()
    events: list[NeuralEvent] = []

    class FakeBridge:
        def observe_environment(self, **kwargs):
            events.append(NeuralEvent("environment", "environment.observed", kwargs))

        def observe_conversation(self, text, **kwargs):
            events.append(NeuralEvent("conversation", "conversation.observed", {"text": text}))

        def observe_task(self, task_id, **kwargs):
            events.append(NeuralEvent("task", "task.observed", {"task_id": task_id}))

        def observe_tool(self, *args, **kwargs):
            events.append(NeuralEvent("terminal", "terminal.observed", {"tool": args[0]}))

        def observe_error(self, error_type, message, **kwargs):
            events.append(NeuralEvent("error", "error.observed", {"error_type": error_type, "message": message}))

    monkeypatch.setattr(plugin, "NeuralRuntimeBridge", FakeBridge)
    plugin._BRIDGES.clear()

    plugin._on_session_start("session-1", turn_id="turn-1")
    plugin._pre_llm_call("session-1", "hello", task_id="task-1", turn_id="turn-1")
    plugin._post_tool_call(
        tool_name="terminal",
        args={"command": "pwd"},
        result="/workspace",
        session_id="session-1",
        task_id="task-1",
        turn_id="turn-1",
        duration_ms=4,
    )

    assert [event.event_type for event in events] == [
        "environment.observed",
        "conversation.observed",
        "task.observed",
        "terminal.observed",
    ]
