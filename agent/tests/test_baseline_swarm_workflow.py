"""SEALED baseline canary for Level 4 Swarm Workflow.

Risk level: 4 (SEALED). Protects the public contract of the deterministic
swarm workflow established by Patch 9. Five classes:

  A. Document  — docs/SWARM_WORKFLOW_BASELINE.md is intact.
  B. Surface   — code modules / classes / loop integration.
  C. Workflow  — dispatch order, evidence validation, no LLM.
  D. Out-of-scope — market data / candlestick / backtest / ambiguous swarm
                    prompts fall through.
  E. Fail-closed — sanitised errors, no web, no LLM fallback.

Failure here means a Level 4 baseline regression.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_BASELINE_DOC = _REPO_ROOT / "docs" / "SWARM_WORKFLOW_BASELINE.md"

_INVARIANT_SUBSTRINGS = (
    "Objective: deterministic pre-LLM workflow for named-preset swarm prompts",
    "Named-preset swarm prompts are intercepted before the LLM/ReAct loop",
    "`swarm_workflow` is the deterministic entrypoint",
    "`run_swarm` must be invoked directly, never by the LLM",
    "The LLM does not decide the first action for named-preset swarm prompts",
    "Dispatch order: `router` → `tool_call(run_swarm)` → `tool_result(run_swarm)` → `validate_report` → `answer`",
    "Success requires `status=completed` from `run_swarm`",
    "Success requires a non-empty `final_report`",
    "Success requires at least one agent task with `status=completed`",
    "`web_search`, `read_url` and `browser` are forbidden",
    "LLM fallback is forbidden",
    "JSON-like tool calls printed as plain text are a regression",
    "Baseline = Patch 9",
    "Level 4 Swarm Workflow — SEALED",
)

_SECRET_SHAPED_BLOCKLIST = (
    "Authorization:", "Bearer ", "token=", "api_key=",
    "secret-", "Traceback", "internal://", "/Users/", "/home/",
    "proxy.local:",
)

_CANONICAL_PROMPT = "Run the crypto_research_lab swarm on ETH with timeframe 30d."

_GOOD_RESULT = {
    "status": "completed",
    "run_id": "canary-run-001",
    "preset": "crypto_research_lab",
    "auto_variables": {"target": "BTC, ETH, SOL", "timeframe": "medium-term 1-3 months"},
    "final_report": "## Alpha Synthesis\nBullish on ETH. Core position: 60% BTC, 20% ETH.\n",
    "tasks": [
        {"id": "task-onchain", "agent_id": "onchain_analyst", "status": "completed", "summary": "On-chain: healthy.", "iterations": 2},
        {"id": "task-defi", "agent_id": "defi_analyst", "status": "completed", "summary": "DeFi: TVL growing.", "iterations": 2},
        {"id": "task-sentiment", "agent_id": "crypto_sentiment_analyst", "status": "completed", "summary": "Sentiment: neutral.", "iterations": 2},
        {"id": "task-alpha", "agent_id": "alpha_synthesizer", "status": "completed", "summary": "Alpha: buy ETH.", "iterations": 2},
    ],
    "token_usage": {"total_input_tokens": 10000, "total_output_tokens": 2000},
}


def _make_registry(result: Any = None, raise_exc: Exception | None = None) -> MagicMock:
    reg = MagicMock()
    if raise_exc is not None:
        reg.execute.side_effect = raise_exc
    else:
        payload = json.dumps(result if result is not None else _GOOD_RESULT)
        reg.execute.return_value = payload
    return reg


class _FakeTrace:
    def __init__(self):
        self.events: list[dict] = []

    def write(self, event: dict) -> None:
        self.events.append(event)


# ---------------------------------------------------------------------------
# Class A — Document
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_baseline_doc_exists() -> None:
    assert _BASELINE_DOC.is_file(), (
        f"Baseline document missing at {_BASELINE_DOC}. "
        "Level 4 Swarm Workflow cannot be SEALED without it."
    )


@pytest.mark.unit
def test_baseline_doc_contains_all_invariant_substrings() -> None:
    text = _BASELINE_DOC.read_text(encoding="utf-8")
    missing = [s for s in _INVARIANT_SUBSTRINGS if s not in text]
    assert not missing, f"Baseline doc is missing invariant substrings: {missing}"


@pytest.mark.unit
def test_baseline_doc_does_not_leak_secrets() -> None:
    text = _BASELINE_DOC.read_text(encoding="utf-8")
    found = [s for s in _SECRET_SHAPED_BLOCKLIST if s in text]
    assert not found, (
        f"Baseline doc contains secret-shaped substrings: {found}."
    )


@pytest.mark.unit
def test_baseline_doc_starts_and_ends_with_sealed_marker() -> None:
    text = _BASELINE_DOC.read_text(encoding="utf-8").strip()
    marker = "Level 4 Swarm Workflow — SEALED"
    first = text.splitlines()[0]
    assert marker in first, f"First line must be the SEALED marker: '{first}'"
    assert text.endswith(marker), (
        f"Last line must be the SEALED marker: '{text.splitlines()[-1]}'"
    )


# ---------------------------------------------------------------------------
# Class B — Surface
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_module_swarm_intent_exports_detector() -> None:
    from src.agent.swarm_intent import (
        SwarmIntent,
        detect_swarm_intent,
    )
    intent = detect_swarm_intent(_CANONICAL_PROMPT)
    assert intent is not None
    assert isinstance(intent, SwarmIntent)
    assert intent.preset_name == "crypto_research_lab"
    assert intent.target == "ETH"
    assert intent.timeframe == "30d"


@pytest.mark.unit
def test_module_swarm_workflow_exports_class() -> None:
    from src.agent.swarm_workflow import SwarmWorkflowDispatcher
    assert SwarmWorkflowDispatcher.ROUTED_BY == "swarm_workflow"


@pytest.mark.unit
def test_swarm_workflow_references_run_swarm() -> None:
    import inspect
    from src.agent import swarm_workflow as wf_mod
    src = inspect.getsource(wf_mod)
    assert "run_swarm" in src, "swarm_workflow.py must reference 'run_swarm'"


@pytest.mark.unit
def test_loop_integrates_swarm_workflow() -> None:
    import inspect
    from src.agent import loop as loop_mod
    src = inspect.getsource(loop_mod)

    assert "SwarmWorkflowDispatcher" in src, "loop.py must import SwarmWorkflowDispatcher"
    assert "SwarmWorkflowDispatcher().try_route" in src, "loop.py must call try_route"

    # Level 1 SEALED defence in depth.
    assert "MarketDataDispatcher" in src, "SEALED contract regressed (Level 1)."
    # Level 2 SEALED defence in depth.
    assert "CandlestickWorkflowDispatcher" in src, "Level 2 SEALED contract regressed."
    # Level 3 SEALED defence in depth.
    assert "BacktestWorkflowDispatcher" in src, "Level 3 SEALED contract regressed."

    # Ordering: market → candlestick → backtest → swarm.
    # Use try_route call sites (not import lines) to get execution order.
    pos_market = src.index("MarketDataDispatcher().try_route")
    pos_candle = src.index("CandlestickWorkflowDispatcher().try_route")
    pos_backtest = src.index("BacktestWorkflowDispatcher().try_route")
    pos_swarm = src.index("SwarmWorkflowDispatcher().try_route")
    assert pos_market < pos_candle < pos_backtest < pos_swarm, (
        "Dispatcher order in loop.py regressed: market < candlestick < backtest < swarm"
    )


# ---------------------------------------------------------------------------
# Class C — Workflow
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_canonical_prompt_dispatches_and_succeeds() -> None:
    from src.agent.swarm_workflow import SwarmWorkflowDispatcher
    reg = _make_registry()
    trace = _FakeTrace()
    result = SwarmWorkflowDispatcher().try_route(_CANONICAL_PROMPT, reg, trace)
    assert result is not None
    assert result["status"] == "success"
    assert result["routed_by"] == "swarm_workflow"
    assert result["iterations"] == 0


@pytest.mark.unit
def test_trace_order_is_canonical() -> None:
    from src.agent.swarm_workflow import SwarmWorkflowDispatcher
    reg = _make_registry()
    trace = _FakeTrace()
    SwarmWorkflowDispatcher().try_route(_CANONICAL_PROMPT, reg, trace)
    ordered = [
        (e.get("event"), e.get("name", ""))
        for e in trace.events
        if e.get("event") in ("router", "tool_call", "tool_result",
                               "workflow_step", "answer", "end")
    ]
    assert ordered[0] == ("router", "swarm_workflow"), f"first event wrong: {ordered[0]}"
    assert ordered[1] == ("tool_call", "run_swarm"), f"second event wrong: {ordered[1]}"
    assert ordered[2] == ("tool_result", "run_swarm"), f"third event wrong: {ordered[2]}"
    assert ordered[3] == ("workflow_step", "validate_report"), f"fourth event wrong: {ordered[3]}"
    assert ordered[4] == ("answer", ""), f"fifth event wrong: {ordered[4]}"
    assert ordered[5] == ("end", ""), f"sixth event wrong: {ordered[5]}"


@pytest.mark.unit
def test_success_requires_completed_tasks_and_final_report() -> None:
    from src.agent.swarm_workflow import SwarmWorkflowDispatcher
    # Empty final_report → fail
    reg = _make_registry({**_GOOD_RESULT, "final_report": ""})
    trace = _FakeTrace()
    result = SwarmWorkflowDispatcher().try_route(_CANONICAL_PROMPT, reg, trace)
    assert result["status"] == "failed", "Empty final_report must fail closed"

    # No completed tasks → fail
    failed_tasks = [{**t, "status": "failed"} for t in _GOOD_RESULT["tasks"]]
    reg2 = _make_registry({**_GOOD_RESULT, "tasks": failed_tasks})
    trace2 = _FakeTrace()
    result2 = SwarmWorkflowDispatcher().try_route(_CANONICAL_PROMPT, reg2, trace2)
    assert result2["status"] == "failed", "Zero completed tasks must fail closed"


@pytest.mark.unit
def test_llm_not_called_for_canonical_prompt() -> None:
    from src.agent.swarm_workflow import SwarmWorkflowDispatcher
    reg = _make_registry()
    trace = _FakeTrace()
    SwarmWorkflowDispatcher().try_route(_CANONICAL_PROMPT, reg, trace)
    # Only run_swarm must have been executed through the registry
    called = [call[0][0] for call in reg.execute.call_args_list]
    assert called == ["run_swarm"], f"Expected only run_swarm, got: {called}"
    # iterations=0 confirms no LLM loop
    end_events = [e for e in trace.events if e.get("type") == "end"]
    assert end_events[0]["iterations"] == 0


# ---------------------------------------------------------------------------
# Class D — Out-of-scope
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.parametrize("prompt", [
    "What is the current price of ETH-USDT?",
    "Show me candlestick patterns for BTC-USDT in the last 60 days.",
    (
        "Backtest a 20/50 MA crossover on BTC-USDT "
        "from 2024-01-01 to 2024-12-31 with 10000 USDT."
    ),
    "Run a swarm on ETH for 30d.",        # missing preset name
    "Analyze ETH with the swarm.",        # missing preset name
])
def test_out_of_scope_prompts_return_none(prompt: str) -> None:
    from src.agent.swarm_workflow import SwarmWorkflowDispatcher
    reg = _make_registry()
    trace = _FakeTrace()
    result = SwarmWorkflowDispatcher().try_route(prompt, reg, trace)
    assert result is None, (
        f"Out-of-scope prompt should not be intercepted: {prompt!r}"
    )
    reg.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Class E — Fail-closed / no-leak
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_run_swarm_exception_is_sanitised() -> None:
    from src.agent.swarm_workflow import SwarmWorkflowDispatcher
    exc_msg = "Authorization: Bearer secret-api-key-12345"
    reg = _make_registry(raise_exc=RuntimeError(exc_msg))
    trace = _FakeTrace()
    result = SwarmWorkflowDispatcher().try_route(_CANONICAL_PROMPT, reg, trace)
    assert result["status"] == "failed"
    assert "Bearer" not in result["content"]
    assert "secret" not in result["content"].lower()


@pytest.mark.unit
def test_run_swarm_error_status_is_sanitised() -> None:
    from src.agent.swarm_workflow import SwarmWorkflowDispatcher
    result_data = {
        "status": "error",
        "error": "Bearer tok-abc123",
        "final_report": "",
        "tasks": [],
    }
    reg = _make_registry(result_data)
    trace = _FakeTrace()
    result = SwarmWorkflowDispatcher().try_route(_CANONICAL_PROMPT, reg, trace)
    assert result["status"] == "failed"
    assert "Bearer" not in result["content"]


@pytest.mark.unit
def test_empty_final_report_fails_closed() -> None:
    from src.agent.swarm_workflow import SwarmWorkflowDispatcher
    reg = _make_registry({**_GOOD_RESULT, "final_report": "   "})
    trace = _FakeTrace()
    result = SwarmWorkflowDispatcher().try_route(_CANONICAL_PROMPT, reg, trace)
    assert result["status"] == "failed"
    assert result["routed_by"] == "swarm_workflow"


@pytest.mark.unit
def test_zero_agents_completed_fails_closed() -> None:
    from src.agent.swarm_workflow import SwarmWorkflowDispatcher
    result_data = {**_GOOD_RESULT, "tasks": []}
    reg = _make_registry(result_data)
    trace = _FakeTrace()
    result = SwarmWorkflowDispatcher().try_route(_CANONICAL_PROMPT, reg, trace)
    assert result["status"] == "failed"


@pytest.mark.unit
def test_json_like_tool_call_text_is_not_success() -> None:
    """Simulate FAIL_MODEL: run_swarm returns JSON-like text instead of
    a valid result dict. The dispatcher must reject it (status != completed)."""
    from src.agent.swarm_workflow import SwarmWorkflowDispatcher
    fake_llm_output = (
        '{"function": "load_skill", "args": {"name": "crypto_research_lab"}}; '
        '{"function": "run_swarm", "args": {"prompt": "..."}}'
    )
    reg = MagicMock()
    reg.execute.return_value = fake_llm_output
    trace = _FakeTrace()
    result = SwarmWorkflowDispatcher().try_route(_CANONICAL_PROMPT, reg, trace)
    assert result["status"] == "failed", (
        "JSON-like tool call text must never be accepted as a successful swarm result"
    )


@pytest.mark.unit
def test_no_web_tools_invoked_on_any_path() -> None:
    from src.agent.swarm_workflow import SwarmWorkflowDispatcher
    for raise_exc in (None, RuntimeError("boom")):
        reg = _make_registry(raise_exc=raise_exc)
        trace = _FakeTrace()
        SwarmWorkflowDispatcher().try_route(_CANONICAL_PROMPT, reg, trace)
        called = [call[0][0] for call in reg.execute.call_args_list]
        for forbidden in ("web_search", "read_url", "browser"):
            assert forbidden not in called, (
                f"Forbidden tool {forbidden!r} was called on path raise_exc={raise_exc}"
            )


@pytest.mark.unit
def test_no_llm_fallback_on_failure() -> None:
    """Dispatcher must never re-enter the LLM loop after run_swarm fails.
    Verified by: result is a dict with status=failed (not None, which would
    cause loop.py to fall through to ReAct)."""
    from src.agent.swarm_workflow import SwarmWorkflowDispatcher
    reg = _make_registry(raise_exc=RuntimeError("swarm exploded"))
    trace = _FakeTrace()
    result = SwarmWorkflowDispatcher().try_route(_CANONICAL_PROMPT, reg, trace)
    assert result is not None, "Dispatcher must return a result, never None, on failure"
    assert result["status"] == "failed"
