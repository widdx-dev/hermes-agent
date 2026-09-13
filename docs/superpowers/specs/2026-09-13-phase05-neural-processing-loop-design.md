# Phase 05 — Neural Processing Loop Design

Status: **Design approved for implementation planning**

Repository: `widdx-dev/hermes-agent`

Baseline: `main` at `126ec5f9d6ac0b1c0c471adabbea6ff95e67f769`

## 1. Goal

Connect selected Hermes lifecycle observations to the existing advisory `NeuralProcessor` through explicit, deterministic processing boundaries, while preserving Hermes as the only execution, approval, and security authority.

## 2. Current Baseline

`NeuralRuntime.sense()` normalizes an observation through a sensory cell, publishes the resulting `NeuralEvent`, and returns it. `NeuralRuntime.process()` already exposes explicit advisory processing through `NeuralProcessor`. The Hermes integration bridge currently uses sensing only; it does not automatically process observations.

Phase 05 therefore adds the smallest missing connection rather than replacing the existing runtime design.

## 3. Architectural Decision

Use **explicit lifecycle processing boundaries**, not immediate per-event processing and not background processing.

The integration should observe lifecycle facts first and process them only at defined boundaries. Processing must remain synchronous, deterministic, best-effort, and isolated from the Hermes execution path.

Preferred boundary model:

```text
Hermes lifecycle event
        ↓
NeuralRuntimeBridge observation
        ↓
NeuralEvent
        ↓
explicit processing boundary
        ↓
NeuralRuntime.process()
        ↓
NeuralSignal[]
```

The processing boundary must never dispatch a Hermes tool or modify Hermes policy state.

## 4. Processing Eligibility

Phase 05 should define a small allowlist of event types eligible for processing rather than processing every event indiscriminately.

Initial eligible observations should correspond to the existing first-party lifecycle cells:

- conversation observations;
- task observations;
- terminal observations;
- error observations;
- environment observations only when the boundary explicitly requests environment processing.

The implementation must make eligibility explicit and testable. An unknown or unsupported event must be ignored rather than becoming an implicit processing trigger.

## 5. Processing Boundaries

The first implementation should expose an explicit bridge/runtime operation representing a processing boundary. The operation receives an already-created `NeuralEvent` and invokes advisory processing only when that event is eligible.

The boundary must:

1. avoid creating a second observation;
2. avoid redispatching Hermes lifecycle events;
3. call only `NeuralRuntime.process()` for eligible events;
4. return advisory signals or an empty result according to the defined interface;
5. catch processor failures so they cannot escape into Hermes.

No background thread, queue, scheduler, or new external dependency is required for Phase 05.

## 6. Signal Handling

`NeuralSignal` remains an advisory output. Phase 05 does not introduce a Hermes decision hook that consumes a signal as authorization or execution input.

Signals may be returned to the neural integration caller for observation/testing, but they must not be passed into tool dispatch, approval, permission, sandbox, or credential paths.

No new signal persistence or cross-session memory behavior is introduced in this phase.

## 7. Error Isolation

There are two independent failure boundaries:

### Observation boundary

Existing bridge sensing remains fail-open. A neural observation failure must return `None` and must not fail the Hermes lifecycle callback.

### Processing boundary

A processor, neuron, or synapse failure must not fail Hermes. The processing boundary should return an empty advisory result when processing cannot complete safely.

Failures must not be converted into Hermes errors, approval decisions, retries, or tool calls.

## 8. Reinforcement

Phase 05 should not introduce automatic reinforcement based on Hermes execution outcomes.

The existing `NeuralRuntime.process()` API supports `reinforce` and `success`; Phase 05 processing boundaries should use the non-reinforcing path by default. Any future reinforcement policy belongs to a later design phase after explicit contracts exist.

## 9. Hard Safety Constraints

Phase 05 must preserve all existing neural integration boundaries.

Processing must not:

- execute a Hermes tool;
- call the Hermes tool dispatcher;
- approve or reject a command;
- mutate approval state;
- modify permissions or sandbox configuration;
- read or write credentials;
- invoke subprocesses;
- perform network access;
- invoke an LLM or external agent;
- replace or alter the Hermes agent loop;
- become a second execution authority.

Tests must explicitly guard these boundaries rather than relying only on code inspection.

## 10. Testing Strategy

TDD is required.

Tests should first prove the desired behavior fails against the current sensing-only integration, then implement the smallest production change.

Required coverage:

1. eligible observation reaches `NeuralProcessor` at the explicit processing boundary;
2. unsupported observations do not reach the processor;
3. processing returns advisory `NeuralSignal` values without execution;
4. processor exceptions are isolated and do not escape the Hermes integration path;
5. processing does not redispatch lifecycle events;
6. processing does not call tool dispatch;
7. processing does not mutate approval/security state;
8. processing does not access credentials;
9. processing does not spawn subprocesses, access the network, or invoke an LLM;
10. existing Phase 04 lifecycle observation tests remain green.

Focused neural tests and Hermes integration tests must pass before the full relevant suite.

CircleCI must be run against the exact final commit used as completion evidence.

## 11. Files / Responsibilities

Expected implementation footprint should remain small:

- `neural/runtime.py` — retain the existing sensing/processing separation; add only the minimum processing-boundary support required by the design.
- `neural/integration.py` — expose the explicit bridge-level processing boundary and isolate processor failures.
- `hermes_cli/observability/neural.py` — connect processing only at the chosen explicit lifecycle boundary; do not move execution ownership into neural code.
- `tests/neural/test_runtime_bridge.py` — processing-boundary and failure-isolation tests.
- `tests/hermes_cli/test_neural_observability.py` — lifecycle integration and execution-safety tests.

If inspection during implementation shows a smaller or more appropriate existing test/module location, preserve established repository structure rather than creating duplicate abstractions.

## 12. Non-Goals

Phase 05 does not implement:

- neural memory integration;
- brain/signal coordination beyond existing processor output;
- guardian behavior changes;
- self-model changes;
- synapse/reflex redesign;
- cross-session learning;
- autonomous neural execution;
- LLM-powered neural reasoning;
- network-dependent processing;
- a neural command-approval system;
- a separate neural agent loop.

## 13. Completion Criteria

Phase 05 may be marked complete only when:

- the processing-boundary contract is implemented;
- TDD coverage exists for routing and isolation;
- focused and relevant full tests pass;
- explicit execution/security boundary tests pass;
- no forbidden side-effect path is introduced;
- CircleCI is green on the exact final commit;
- the roadmap is updated from `NEXT` to `COMPLETED` using that evidence.

Until those conditions are met, Phase 05 remains in progress.
