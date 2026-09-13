# Phase 05 — Neural Processing Loop Implementation Plan

> **For the implementation agent:** Follow this plan task-by-task. Apply TDD: write each failing test before the smallest production change that makes it pass. Do not start Phase 06 or any deferred neural scope.

**Goal:** Connect selected Hermes lifecycle observations to the existing advisory `NeuralProcessor` through explicit, deterministic processing boundaries while keeping Hermes as the sole execution, approval, and security authority.

**Architecture:** Hermes lifecycle observation remains separate from neural processing. `NeuralRuntimeBridge` observes first and exposes an explicit processing-boundary operation for an already-created `NeuralEvent`. Eligible events are processed synchronously through `NeuralRuntime.process()` with reinforcement disabled. Processor failures are swallowed at the neural integration boundary and cannot become Hermes failures. No queue, thread, scheduler, LLM, network, subprocess, tool dispatch, approval mutation, permission change, credential access, or new external dependency is introduced.

**Baseline:** `main` after the Phase 05 design/roadmap documentation merge. Existing runtime already separates `sense()` from `process()`, and the Hermes bridge currently performs sensing only. Existing Phase 04 tests must remain green.

---

## Task 1 — Add failing processing-boundary contract tests

**Files:**
- Modify: `tests/neural/test_runtime_bridge.py`

**Step 1: Write the failing tests.**

Add tests that define the public bridge behavior before changing production code:

1. An eligible `NeuralEvent` returned by an observation reaches the processor only when the explicit processing-boundary method is called.
2. Processing receives the exact already-created event; the boundary must not call `sense()` or create a second event.
3. Conversation, task, terminal, and error events are eligible.
4. Environment events are processed only when the boundary explicitly allows environment processing.
5. An unsupported/unknown event returns an empty signal list and does not call the processor.
6. Processor output is returned as advisory `NeuralSignal` values.
7. Processor exceptions are isolated and produce an empty result.
8. Processing does not enable reinforcement automatically; assert the processor is called with `reinforce=False` and the default success behavior.

Use a small fake/stub processor or monkeypatch the existing processor method rather than adding a new production abstraction.

**Step 2: Run the focused tests.**

Run only the relevant bridge test file. The new tests must fail against the current sensing-only bridge. Existing tests that cover Phase 04 should remain green.

**Step 3: Confirm the failure is the intended missing behavior.**

Do not change production code to make unrelated failures disappear. The failure should demonstrate that the explicit processing boundary does not yet exist.

---

## Task 2 — Implement the minimal bridge processing boundary

**Files:**
- Modify: `neural/integration.py`
- Modify: `neural/runtime.py` only if inspection proves a runtime helper is necessary

**Step 1: Define explicit eligibility in one place.**

Use the existing event-type names emitted by the sensory cells. Keep the allowlist small and explicit:

- `conversation.observed`
- `task.observed`
- `terminal.observed`
- `error.observed`
- `environment.observed` only when explicitly requested by the boundary caller

Unknown event types must be ignored.

**Step 2: Add the bridge operation for an already-created event.**

Add one explicit bridge-level method, with a clear name such as `process_event(...)`, whose input is the existing `NeuralEvent`. It must:

- check eligibility;
- call `self.runtime.process(event, reinforce=False)`;
- return the resulting `list[NeuralSignal]`;
- never call an observation method;
- never redispatch Hermes lifecycle hooks;
- catch `Exception` around processing and return `[]`.

If the chosen interface uses an explicit `include_environment`/equivalent flag, default it to false so environment processing is opt-in.

**Step 3: Keep `NeuralRuntime` unchanged unless required.**

The existing `NeuralRuntime.process()` already provides the required advisory processor call. Prefer not to add another wrapper or duplicate processing API. If a runtime helper is genuinely necessary, make it a thin deterministic eligibility/boundary primitive and preserve the existing `sense()`/`process()` separation.

**Step 4: Run focused tests.**

Run `tests/neural/test_runtime_bridge.py`. All existing and new tests should pass.

---

## Task 3 — Connect processing at the explicit Hermes lifecycle boundary

**Files:**
- Modify: `hermes_cli/observability/neural.py`
- Modify: `tests/hermes_cli/test_neural_observability.py`

**Step 1: Write failing lifecycle integration tests.**

Define exactly where processing occurs. The implementation must use a deterministic synchronous lifecycle boundary rather than processing every individual observation immediately or creating background work.

Tests must prove:

1. lifecycle observation happens first;
2. the resulting `NeuralEvent` is passed to the explicit processing boundary;
3. no second observation is created;
4. processing is not performed for an unsupported event;
5. processor failure does not escape `observe_lifecycle()`;
6. `on_session_end` still performs bridge cleanup without introducing post-cleanup processing.

Keep the tests compatible with the existing fake bridge pattern.

**Step 2: Implement the smallest lifecycle connection.**

At the chosen explicit boundary, retain the current lifecycle-to-cell mappings and then call the bridge processing method with the event that was just returned by the observation method. Do not restructure Hermes lifecycle dispatch.

The implementation must not call processing from inside every low-level observation helper unless that is the explicitly selected boundary. The point of Phase 05 is to make processing boundaries visible and deterministic.

**Step 3: Preserve fail-open behavior.**

If the bridge returns `None` for an observation, do not attempt processing. If processing raises unexpectedly despite the bridge's own isolation, the Hermes observer must remain best-effort and non-fatal.

**Step 4: Run focused Hermes/neural tests.**

Run:
- `tests/neural/test_runtime_bridge.py`
- `tests/hermes_cli/test_neural_observability.py`

---

## Task 4 — Add explicit execution and security boundary regression tests

**Files:**
- Modify: `tests/neural/test_runtime_bridge.py`
- Modify: `tests/hermes_cli/test_neural_observability.py`

**Step 1: Write tests that fail if forbidden side effects are introduced.**

Guard the processing path against:

- Hermes tool dispatch;
- command approval/rejection;
- approval-state mutation;
- permission or sandbox mutation;
- credential access;
- subprocess creation;
- network access;
- LLM/external-agent invocation;
- lifecycle redispatch.

Use monkeypatches/spies against the relevant existing interfaces where they exist. Do not introduce fake production security APIs solely for testing.

**Step 2: Verify advisory-only signal handling.**

Assert that returned `NeuralSignal` objects remain return values for callers/tests and are not handed to any Hermes execution or approval mechanism.

**Step 3: Verify no automatic reinforcement.**

Add/retain an assertion that Phase 05 processing does not reinforce synapses or alter success state based on lifecycle outcomes.

**Step 4: Run the focused regression suite.**

All neural processing and Hermes observability tests must pass, including the existing Phase 04 tests.

---

## Task 5 — Run the relevant full suite and inspect the final diff

**Files:**
- No production changes unless failures expose a defect in Tasks 1–4.

**Step 1: Run focused tests first.**

Confirm the neural bridge and Hermes observability tests are green.

**Step 2: Run the relevant full test suite.**

Use the repository's existing test commands and include the complete neural test suite plus the Hermes observability/lifecycle tests. Do not substitute stale CI evidence for local verification.

**Step 3: Run repository quality checks.**

Use the existing project commands for lint/type checks/formatting where applicable. Do not introduce a new toolchain for Phase 05.

**Step 4: Inspect the final diff against `main`.**

Confirm the implementation footprint remains limited to the planned neural runtime/integration and observability/test files. Explicitly check that there are no:

- subprocess/network/LLM dependencies;
- tool-dispatch calls;
- approval/security mutations;
- credential reads/writes;
- background queues/threads/schedulers;
- Phase 06+ memory or learning behavior.

**Step 5: Verify the exact commit in CircleCI.**

Push the final commit to the established repository workflow and use CircleCI's result for that exact commit as completion evidence. GitHub Actions is not a required evidence source for this project.

**Step 6: Update the roadmap only after evidence exists.**

Only after all tests and CircleCI verification pass, update `docs/WIDDX_NEURAL_ROADMAP.md` to mark Phase 05 `COMPLETED`, recording the exact completion commit and verification evidence. Do not update Phase 06 status.

---

## Final verification checklist

Before declaring Phase 05 complete, verify all of the following:

- [ ] explicit processing-boundary contract exists;
- [ ] eligible events are allowlisted and test-covered;
- [ ] unsupported events are ignored;
- [ ] existing `NeuralEvent` is processed without re-observation;
- [ ] `NeuralRuntime.process()` is the advisory processing path;
- [ ] reinforcement remains disabled by default;
- [ ] processor failures return an empty advisory result and cannot break Hermes;
- [ ] no lifecycle redispatch occurs;
- [ ] no tool dispatch occurs;
- [ ] no approval/security mutation occurs;
- [ ] no credential access occurs;
- [ ] no subprocess/network/LLM/external-agent activity occurs;
- [ ] no background queue/thread/scheduler is introduced;
- [ ] Phase 04 tests remain green;
- [ ] focused tests pass;
- [ ] relevant full suite passes;
- [ ] quality checks pass;
- [ ] CircleCI is green for the exact final commit;
- [ ] roadmap is updated only after the above evidence.

**Do not mark Phase 05 complete from the existence of this plan.**