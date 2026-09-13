# WIDDX Neural Foundation Roadmap

Status: **Roadmap baseline — planning only**

Repository: `widdx-dev/hermes-agent`

Last verified baseline: `main` at merge commit `126ec5f9d6ac0b1c0c471adabbea6ff95e67f769`

## 1. Purpose

WIDDX Neural Foundation is a first-party neural/advisory layer inside Hermes Agent. Hermes remains the execution, security, approval, and tool-dispatch core.

The neural layer is designed to continuously observe and process agent experience without becoming an execution authority.

### Hard architectural boundaries

The neural layer must not:

- execute tools;
- approve or reject commands on behalf of Hermes;
- modify permissions, approval state, sandbox configuration, or credentials;
- invoke an LLM, network service, subprocess, or external agent as part of observation/processing;
- become a second agent runtime competing with Hermes.

Neural functionality should remain additive, deterministic where practical, fail-open at the Hermes integration boundary, and independently testable.

## 2. Completed foundation

### Phase 01 — Neural Event Contracts

**Status: COMPLETED**

Established the foundational `NeuralEvent` / `NeuralSignal` contracts and payload isolation rules.

Delivered through PR #1.

### Phase 02 — Sensory Cells v1

**Status: COMPLETED**

Established the initial sensory layer, including:

- `ConversationCell`
- `TaskCell`
- `TerminalCell`
- `ErrorCell`
- `EnvironmentCell`
- common `SensoryCell` behavior

Delivered through PR #2.

### Phase 03 — Runtime + Advisory Processing Foundation

**Status: COMPLETED / BASELINE**

Established the first runtime composition around:

- `NeuralRuntime`
- `NeuralBus`
- `NeuralProcessor`
- `Brain`
- `Memory`
- `Guardian`
- `SelfModel`
- neuron/reflex/synapse foundations

The runtime exposes observation/sensing separately from processing. `sense()` publishes observations; processing remains an explicit advisory operation.

### Phase 04 — Hermes First-Party Neural Integration

**Status: COMPLETED**

PR #8 connected the neural foundation to Hermes lifecycle observability.

Merged commit:

`126ec5f9d6ac0b1c0c471adabbea6ff95e67f769`

Integrated lifecycle coverage:

| Hermes lifecycle | Neural observation |
|---|---|
| `on_session_start` | Environment |
| `pre_llm_call` | Conversation + Task |
| `post_tool_call` | Terminal + Error when applicable |
| `on_session_end` | Bridge cleanup |

The integration is always-on, execution-free, and fail-open. Neural failures must not break the primary Hermes path.

CircleCI neural tests were green on the final PR head before merge.

## 3. Next phases

The following phases are intentionally ordered. A phase must not be marked complete until its tests and verification evidence exist.

### Phase 05 — Neural Processing Loop

**Status: NEXT**

Goal: connect observed Hermes lifecycle facts to the existing advisory processing pipeline without giving neural processing execution authority.

Scope:

- define when an observed `NeuralEvent` is eligible for processing;
- establish deterministic processing boundaries for session/turn/tool observations;
- route selected observations through `NeuralProcessor`;
- preserve the separation between sensing, processing, and Hermes execution;
- define error isolation so processor failures cannot affect Hermes;
- add tests proving no tool dispatch, approval mutation, credential access, subprocess, network, or LLM invocation occurs.

Non-goals:

- autonomous tool execution;
- autonomous command approval;
- LLM calls;
- external network calls;
- replacing Hermes decision/execution logic.

Exit criteria:

- processing-loop contract documented;
- TDD coverage for event-to-processing routing;
- fail-open behavior verified;
- execution/security boundary tests pass;
- CircleCI green on the exact final commit.

### Phase 06 — Neural Memory Integration

**Status: PLANNED**

Goal: make the existing neural memory component useful for structured advisory state while preserving explicit ownership and isolation.

Scope:

- define what observations are memory-worthy;
- establish memory write/read boundaries;
- preserve session and correlation identity;
- prevent uncontrolled memory growth;
- define retention/eviction behavior;
- test isolation between sessions.

Important constraint: memory must not silently become a second source of truth for Hermes security, permissions, or execution state.

### Phase 07 — Brain / Signal Coordination

**Status: PLANNED**

Goal: turn processed observations into coherent advisory `NeuralSignal` outputs using the existing brain/processor abstractions.

Scope:

- deterministic signal generation;
- signal prioritization and confidence;
- correlation of conversation, task, terminal, error, and environment observations;
- signal lifecycle and deduplication;
- explicit distinction between advisory signals and Hermes decisions.

No direct execution path is introduced.

### Phase 08 — Guardian Safety Layer

**Status: PLANNED**

Goal: formalize the neural-side safety boundary around observations, processing, memory, and signals.

Scope:

- validate neural inputs and outputs;
- enforce non-execution invariants;
- detect prohibited side effects;
- define fail-closed behavior inside neural safety components while keeping the Hermes integration fail-open;
- security regression tests.

The Guardian must not become Hermes's command-approval mechanism.

### Phase 09 — Self Model

**Status: PLANNED**

Goal: use the existing `SelfModel` foundation to maintain a bounded advisory representation of neural runtime state and learned operational patterns.

Scope:

- define self-model facts;
- confidence and provenance;
- update rules;
- reset/session boundaries;
- protection against self-model contamination by arbitrary tool output.

No self-model fact may directly change Hermes permissions or execution policy.

### Phase 10 — Synapses and Reflexes

**Status: PLANNED**

Goal: establish deterministic relationships between recurring neural patterns and advisory responses.

Scope:

- explicit synapse contracts;
- bounded reflex rules;
- pattern matching and correlation;
- reinforcement only through controlled, testable interfaces;
- prevention of reflexes becoming hidden tool-execution paths.

### Phase 11 — Cross-Session Learning Foundation

**Status: PLANNED / LATER**

Goal: allow useful neural knowledge to persist across sessions in a controlled manner.

Scope will be defined only after Phases 05–10 provide sufficient contracts and safety evidence.

Potential concerns to resolve before implementation:

- privacy and secret redaction;
- retention limits;
- provenance;
- stale knowledge;
- conflict resolution;
- deterministic replay/testing.

No autonomous online learning or external model training is implied by this phase.

### Phase 12 — Hermes Advisory Surface

**Status: PLANNED / LATER**

Goal: expose selected neural signals to Hermes in a clearly advisory form.

The surface must make it impossible to confuse a neural suggestion with an authorization or execution decision.

Scope may include:

- structured advisory context;
- diagnostics/observability;
- explainable signal provenance;
- explicit confidence and uncertainty.

## 4. Global verification policy

Every phase follows the same development discipline:

1. Inspect the actual repository state before planning implementation.
2. Read the relevant architecture and test contracts before changing code.
3. Write failing tests first for new behavior.
4. Implement the smallest production change that satisfies the tests.
5. Run focused tests, then the relevant full suite.
6. Verify the neural safety boundaries explicitly.
7. Run CircleCI and use the exact tested commit as evidence.
8. Do not mark a phase `COMPLETED` from a plan, local assumption, or stale CI result.
9. Update this roadmap only when the phase state is supported by repository evidence.

## 5. Explicitly deferred

These are outside the current roadmap until a later design decision:

- autonomous neural tool execution;
- neural command approval;
- neural modification of Hermes security policy;
- direct credential management;
- external LLM calls from the neural runtime;
- network-dependent neural processing;
- replacing Hermes's agent loop;
- building a separate competing neural agent;
- Phase 09/AI-style future scope without an approved design.

## 6. Current state

**Current phase: Phase 05 — Neural Processing Loop**

Phase 05 has not started yet. This file defines the roadmap only; it does not claim implementation, tests, or completion for Phase 05.
