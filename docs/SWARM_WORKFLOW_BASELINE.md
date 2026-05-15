# Level 4 Swarm Workflow — SEALED

Status: **SEALED** as of PR #10.
Baseline = Patch 9.

This document is a contract. Any change that breaks one of the fourteen
invariants below must explicitly bump the baseline (new SEALED PR), not
silently regress.

The anti-regression canary lives at:

```
pytest agent/tests/test_baseline_swarm_workflow.py -v
```

Run it locally before any PR that touches `agent/src/agent/loop.py`,
`agent/src/agent/swarm_intent.py`,
`agent/src/agent/swarm_workflow.py`, or
`agent/src/tools/swarm_tool.py`.

---

## 1. Objective: deterministic pre-LLM workflow for named-preset swarm prompts

The agent must execute named-preset swarm prompts deterministically by invoking
`run_swarm` directly — without depending on the LLM/ReAct loop to call
`run_swarm` or orchestrate sub-agents. Local LLMs (7B / 8B) were empirically
unable to invoke `run_swarm` correctly; instead they printed JSON-like tool
calls as plain text, producing a false-positive success with zero agent
execution. Patch 9 replaces that unreliable LLM call with deterministic code.

## 2. Named-preset swarm prompts are intercepted before the LLM/ReAct loop

`AgentLoop.run()` invokes `SwarmWorkflowDispatcher().try_route(...)` after the
`BacktestWorkflowDispatcher` short-circuit and before the ReAct `while` loop.
If the dispatcher returns a result dict, the loop short-circuits and the LLM
is never called. If it returns `None`, the ReAct loop runs unchanged.

## 3. `swarm_workflow` is the deterministic entrypoint

Defined in `agent/src/agent/swarm_workflow.py` as
`SwarmWorkflowDispatcher.ROUTED_BY = "swarm_workflow"`. The dispatcher emits
trace events tagged with this name so any auditing tool can filter on it.

## 4. `run_swarm` must be invoked directly, never by the LLM

The dispatcher calls `registry.execute("run_swarm", {"prompt": user_message})`
directly from Python code. It is never delegated to the LLM to decide when or
whether to call `run_swarm`. Any path where the LLM emits the tool call is a
baseline regression.

## 5. The LLM does not decide the first action for named-preset swarm prompts

The dispatcher intercepts before the ReAct while-loop. The short-circuit
result carries `iterations == 0` and `routed_by == "swarm_workflow"`. An
`iterations > 0` result for a canonical swarm prompt is a regression.

## 6. Dispatch order: `router` → `tool_call(run_swarm)` → `tool_result(run_swarm)` → `validate_report` → `answer`

The dispatcher emits trace events in this strict order. Any inversion or skip
is immediately visible in the trace and is a baseline regression.

## 7. Success requires `status=completed` from `run_swarm`

The dispatcher only proceeds to answer when the parsed `run_swarm` result
carries `status == "completed"`. Results with `status` equal to `"failed"`,
`"error"`, `"timeout"`, or `"cancelled"` trigger a fail-closed error response.

## 8. Success requires a non-empty `final_report`

The `final_report` field of the `run_swarm` result must be a non-empty,
non-whitespace string. An empty or whitespace-only `final_report` triggers a
fail-closed error. Returning a fabricated or template-filled report string
without real agent execution is a regression equivalent to fabricating a
verdict.

## 9. Success requires at least one agent task with `status=completed`

The `tasks` array from `run_swarm` must contain at least one element where
`task["status"] == "completed"`. A result with an empty `tasks` list or with
all tasks in a non-completed state is a regression.

## 10. `web_search`, `read_url` and `browser` are forbidden

For any prompt the dispatcher accepts, the only external tool invoked is
`run_swarm`. On success, failure, or exception, the dispatcher never calls
`web_search`, `read_url`, or any browser primitive.

## 11. LLM fallback is forbidden

If `run_swarm` raises an exception or returns a non-completed status, the
dispatcher returns a sanitised `{"status": "failed"}` result. It never falls
through to the LLM/ReAct loop as a recovery path.

## 12. JSON-like tool calls printed as plain text are a regression

The dispatcher exists specifically to prevent the FAIL_MODEL pattern observed
in smoke testing, where `llama3.1:8b` printed tool call JSON as the answer
body and the loop marked `status=success` with zero actual execution. Any path
that accepts plain-text tool call syntax as a valid swarm result is a
regression.

## 13. Baseline = Patch 9

| PR | Layer | Concern |
|----|-------|---------|
| #9 | Pre-LLM workflow | `SwarmWorkflowDispatcher` invokes `run_swarm` directly, validates `status=completed` + non-empty `final_report` + completed tasks. |
| #10 | **SEALED** | This document + the anti-regression canary. |

Patch 9 must remain present and integrated in `AgentLoop.run`. Removing the
dispatcher invocation or any of its validation steps is a baseline regression.

## 14. Residual risk

The dispatcher validates execution structure (that `run_swarm` ran, that agents
reported status, that a report exists). It does not validate the factual
correctness of agent outputs. Content quality depends on the underlying model
and swarm preset configuration, which are outside the scope of this baseline.

---

## Anti-regression test

The canary `agent/tests/test_baseline_swarm_workflow.py` has five classes:

- **Class A — Document**: this file exists, contains the fourteen invariant
  substrings, does not leak credentials, and is bounded by identical SEALED
  markers.
- **Class B — Surface**: `swarm_intent`, `swarm_workflow`, and
  `SwarmWorkflowDispatcher` are present in code; `AgentLoop` integrates the
  dispatcher; `run_swarm` is referenced in the workflow source.
- **Class C — Workflow**: canonical prompt drives the dispatcher; trace records
  the five steps in exact order; success requires completed tasks and non-empty
  final_report; no LLM is called.
- **Class D — Out-of-scope**: market data, candlestick, backtest, and ambiguous
  swarm prompts (without explicit preset name) return `None` from `try_route` —
  the ReAct loop runs as before.
- **Class E — Fail-closed**: poisoned error is sanitised against the
  credential-pattern blocklist; empty `final_report` fails closed; zero
  completed tasks fails closed; JSON-like tool call text is rejected; no web
  tool is invoked on any error path.

Run:

```
pytest agent/tests/test_baseline_swarm_workflow.py -v
```

A green run means Level 4 Swarm Workflow is intact. A red run means a
baseline regression — investigate before merging.

---

## 15. Evidence Quality Gate — Patch 15

Added in Patch 15 as a post-validation layer inside `SwarmWorkflowDispatcher`.
Implemented in `agent/src/agent/swarm_evidence_gate.py`.

### What it validates

The gate evaluates the corpus formed by `final_report` + all task `summary`
fields (concatenated, lower-cased) for the presence of **evidence keywords**:
financial terms, asset names, metric labels, and analytical indicators. It also
checks for **limitation keywords** in `final_report` as an advisory signal.

| Check | Keywords source | Failure mode |
|---|---|---|
| Evidence keywords | `_EVIDENCE_KEYWORDS` (frozenset, ~30 terms) | gate=partial → dispatcher status=partial |
| Limitation keywords | `_LIMITATION_KEYWORDS` (frozenset, ~15 terms) | warnings=["no_limitations_section"] (advisory; gate remains pass) |
| Empty report | n/a | gate=fail → dispatcher status=failed |

### What it does NOT validate

- Factual correctness of on-chain data, DeFi TVL, or sentiment scores.
- Whether the cited sources are real or accessible.
- Whether the numeric values are accurate.
- Whether the report reflects a specific time period correctly.

### Gate status → dispatcher status

| Gate status | Dispatcher status |
|---|---|
| pass | success |
| partial | partial |
| fail | failed |

### Fail-closed properties

- Gate runs before `answer` and `end` events are emitted.
- Gate exception → propagated as failed (never suppressed).
- Gate result is included in the return dict as `evidence_gate`.
- Trace event: `quality_gate` (event type not captured by the canonical trace filter).
- No LLM fallback on gate partial or fail.
- No web tool invoked by the gate.

### Residual risk

Keyword matching is structural, not semantic. A report that contains one of the
evidence keywords but no meaningful analysis will still pass. The gate is a
minimum bar, not a quality audit. Content accuracy remains outside this baseline.

---

Level 4 Swarm Workflow — SEALED
