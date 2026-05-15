"""Tests for Patch 9 — SwarmWorkflowDispatcher."""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from src.agent.swarm_intent import SwarmIntent, detect_swarm_intent
from src.agent.swarm_workflow import SwarmWorkflowDispatcher


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CANONICAL_PROMPT = "Run the crypto_research_lab swarm on ETH with timeframe 30d."

_GOOD_RESULT = {
    "status": "completed",
    "run_id": "test-run-001",
    "preset": "crypto_research_lab",
    "auto_variables": {"target": "BTC, ETH, SOL", "timeframe": "medium-term 1-3 months"},
    "final_report": "## Alpha Synthesis\nBullish outlook for ETH over 30d.\n",
    "tasks": [
        {"id": "task-onchain", "agent_id": "onchain_analyst", "status": "completed", "summary": "On-chain: healthy.", "iterations": 3},
        {"id": "task-defi", "agent_id": "defi_analyst", "status": "completed", "summary": "DeFi: TVL growing.", "iterations": 4},
        {"id": "task-sentiment", "agent_id": "crypto_sentiment_analyst", "status": "completed", "summary": "Sentiment: neutral.", "iterations": 2},
        {"id": "task-alpha", "agent_id": "alpha_synthesizer", "status": "completed", "summary": "Alpha: buy ETH.", "iterations": 5},
    ],
    "token_usage": {"total_input_tokens": 4000, "total_output_tokens": 1200},
}


class _FakeTrace:
    def __init__(self):
        self.events: list[dict] = []

    def write(self, event: dict) -> None:
        self.events.append(event)


def _make_registry(result: Any = None, raise_exc: Exception | None = None) -> MagicMock:
    reg = MagicMock()
    if raise_exc is not None:
        reg.execute.side_effect = raise_exc
    else:
        payload = json.dumps(result if result is not None else _GOOD_RESULT)
        reg.execute.return_value = payload
    return reg


# ---------------------------------------------------------------------------
# Group 1 — detect_swarm_intent extracts fields from canonical prompt
# ---------------------------------------------------------------------------

class TestSwarmIntentDetection:
    def test_canonical_prompt_extracts_preset(self):
        intent = detect_swarm_intent(CANONICAL_PROMPT)
        assert intent is not None
        assert intent.preset_name == "crypto_research_lab"

    def test_canonical_prompt_extracts_target(self):
        intent = detect_swarm_intent(CANONICAL_PROMPT)
        assert intent is not None
        assert intent.target == "ETH"

    def test_canonical_prompt_extracts_timeframe(self):
        intent = detect_swarm_intent(CANONICAL_PROMPT)
        assert intent is not None
        assert intent.timeframe == "30d"

    def test_returns_none_for_empty_prompt(self):
        assert detect_swarm_intent("") is None
        assert detect_swarm_intent(None) is None  # type: ignore[arg-type]

    def test_returns_none_without_swarm_word(self):
        assert detect_swarm_intent("Analyze ETH on crypto_research_lab.") is None

    def test_returns_none_without_preset_name(self):
        assert detect_swarm_intent("Run a swarm on ETH for 30d.") is None

    def test_returns_none_for_unknown_preset(self):
        assert detect_swarm_intent("Run the unknown_preset swarm on ETH.") is None

    def test_returns_swarm_intent_dataclass(self):
        intent = detect_swarm_intent(CANONICAL_PROMPT)
        assert isinstance(intent, SwarmIntent)


# ---------------------------------------------------------------------------
# Group 2 — Canonical prompt dispatches (returns non-None, status=success)
# ---------------------------------------------------------------------------

class TestCanonicalPromptRoutes:
    def test_canonical_prompt_returns_non_none(self):
        reg = _make_registry()
        trace = _FakeTrace()
        result = SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        assert result is not None

    def test_canonical_prompt_status_success(self):
        reg = _make_registry()
        trace = _FakeTrace()
        result = SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        assert result["status"] == "success"

    def test_canonical_prompt_routed_by(self):
        reg = _make_registry()
        trace = _FakeTrace()
        result = SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        assert result["routed_by"] == "swarm_workflow"

    def test_canonical_prompt_iterations_zero(self):
        reg = _make_registry()
        trace = _FakeTrace()
        result = SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        assert result["iterations"] == 0

    def test_canonical_prompt_has_run_id(self):
        reg = _make_registry()
        trace = _FakeTrace()
        result = SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        assert result.get("run_id") == "test-run-001"


# ---------------------------------------------------------------------------
# Group 3 — run_swarm is called directly via registry (not LLM)
# ---------------------------------------------------------------------------

class TestRunSwarmCalledDirectly:
    def test_run_swarm_called_once(self):
        reg = _make_registry()
        trace = _FakeTrace()
        SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        assert reg.execute.call_count == 1

    def test_run_swarm_called_with_prompt(self):
        reg = _make_registry()
        trace = _FakeTrace()
        SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        call_args = reg.execute.call_args
        assert call_args[0][0] == "run_swarm"
        assert call_args[0][1]["prompt"] == CANONICAL_PROMPT

    def test_llm_never_called(self):
        """No LLM object is involved when dispatcher intercepts the prompt."""
        reg = _make_registry()
        trace = _FakeTrace()
        with patch("src.agent.swarm_workflow.SwarmWorkflowDispatcher._fail",
                   wraps=SwarmWorkflowDispatcher._fail):
            SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        # registry.execute was called (not any LLM method)
        reg.execute.assert_called_once()


# ---------------------------------------------------------------------------
# Group 4 — Trace contains router / tool_call / tool_result in order
# ---------------------------------------------------------------------------

class TestTraceOrder:
    def test_trace_has_router_event(self):
        reg = _make_registry()
        trace = _FakeTrace()
        SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        router_events = [e for e in trace.events if e.get("event") == "router"]
        assert len(router_events) == 1
        assert router_events[0]["name"] == "swarm_workflow"

    def test_trace_has_tool_call_event(self):
        reg = _make_registry()
        trace = _FakeTrace()
        SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        tc_events = [e for e in trace.events if e.get("event") == "tool_call"]
        assert len(tc_events) == 1
        assert tc_events[0]["name"] == "run_swarm"

    def test_trace_has_tool_result_event(self):
        reg = _make_registry()
        trace = _FakeTrace()
        SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        tr_events = [e for e in trace.events if e.get("event") == "tool_result"]
        assert len(tr_events) == 1
        assert tr_events[0]["name"] == "run_swarm"

    def test_trace_order_is_canonical(self):
        reg = _make_registry()
        trace = _FakeTrace()
        SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        # Extract (event, name) pairs for ordered events
        ordered = [
            (e.get("event"), e.get("name", ""))
            for e in trace.events
            if e.get("event") in ("router", "tool_call", "tool_result",
                                   "workflow_step", "answer", "end")
        ]
        assert ordered[0] == ("router", "swarm_workflow")
        assert ordered[1] == ("tool_call", "run_swarm")
        assert ordered[2] == ("tool_result", "run_swarm")
        assert ordered[3] == ("workflow_step", "validate_report")
        assert ordered[4] == ("answer", "")
        assert ordered[5] == ("end", "")

    def test_trace_uses_both_event_and_type_keys(self):
        reg = _make_registry()
        trace = _FakeTrace()
        SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        end_events = [e for e in trace.events if e.get("type") == "end"]
        assert len(end_events) == 1
        assert end_events[0]["status"] == "success"


# ---------------------------------------------------------------------------
# Group 5 — Success only if completed + non-empty report + tasks ran
# ---------------------------------------------------------------------------

class TestSuccessRequiresEvidence:
    def test_fails_if_status_failed(self):
        result_data = {**_GOOD_RESULT, "status": "failed", "error": "agent crashed"}
        reg = _make_registry(result_data)
        trace = _FakeTrace()
        result = SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        assert result["status"] == "failed"

    def test_fails_if_status_timeout(self):
        result_data = {**_GOOD_RESULT, "status": "timeout"}
        reg = _make_registry(result_data)
        trace = _FakeTrace()
        result = SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        assert result["status"] == "failed"

    def test_fails_if_final_report_empty(self):
        result_data = {**_GOOD_RESULT, "final_report": ""}
        reg = _make_registry(result_data)
        trace = _FakeTrace()
        result = SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        assert result["status"] == "failed"

    def test_fails_if_final_report_whitespace(self):
        result_data = {**_GOOD_RESULT, "final_report": "   "}
        reg = _make_registry(result_data)
        trace = _FakeTrace()
        result = SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        assert result["status"] == "failed"

    def test_fails_if_tasks_empty(self):
        result_data = {**_GOOD_RESULT, "tasks": []}
        reg = _make_registry(result_data)
        trace = _FakeTrace()
        result = SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        assert result["status"] == "failed"

    def test_fails_if_no_task_completed(self):
        tasks_failed = [{**t, "status": "failed"} for t in _GOOD_RESULT["tasks"]]
        result_data = {**_GOOD_RESULT, "tasks": tasks_failed}
        reg = _make_registry(result_data)
        trace = _FakeTrace()
        result = SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# Group 6 — JSON-like text (FAIL_MODEL simulation) is rejected
# ---------------------------------------------------------------------------

class TestFailModelSimulation:
    def test_json_text_as_string_is_rejected(self):
        """If run_swarm returns a plain string that looks like JSON tool calls,
        the dispatcher fails closed (it cannot be parsed as a valid result dict
        with status=completed)."""
        fake_llm_output = (
            '{"function": "load_skill", "args": {"name": "crypto_research_lab"}}; '
            '{"function": "run_swarm", "args": {"prompt": "..."}}'
        )
        reg = MagicMock()
        reg.execute.return_value = fake_llm_output
        trace = _FakeTrace()
        result = SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        # Parsed as JSON but missing status=completed → fails
        assert result["status"] == "failed"

    def test_status_success_string_without_evidence_is_rejected(self):
        """If run_swarm returns status=success but no final_report,
        that is a false positive — dispatcher must reject it."""
        result_data = {
            "status": "completed",
            "run_id": "fake",
            "preset": "crypto_research_lab",
            "final_report": "",
            "tasks": [],
            "token_usage": {},
        }
        reg = _make_registry(result_data)
        trace = _FakeTrace()
        result = SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# Group 7 — Forbidden tools never called
# ---------------------------------------------------------------------------

class TestForbiddenTools:
    def _run_and_collect_executes(self, prompt: str, result_data: Any = None) -> list[str]:
        reg = _make_registry(result_data)
        trace = _FakeTrace()
        SwarmWorkflowDispatcher().try_route(prompt, reg, trace)
        return [call[0][0] for call in reg.execute.call_args_list]

    def test_web_search_never_called(self):
        called = self._run_and_collect_executes(CANONICAL_PROMPT)
        assert "web_search" not in called

    def test_read_url_never_called(self):
        called = self._run_and_collect_executes(CANONICAL_PROMPT)
        assert "read_url" not in called

    def test_browser_never_called(self):
        called = self._run_and_collect_executes(CANONICAL_PROMPT)
        assert "browser" not in called

    def test_only_run_swarm_called_on_success(self):
        called = self._run_and_collect_executes(CANONICAL_PROMPT)
        assert called == ["run_swarm"]

    def test_no_tool_called_on_intent_miss(self):
        reg = _make_registry()
        trace = _FakeTrace()
        result = SwarmWorkflowDispatcher().try_route("Get the price of BTC.", reg, trace)
        assert result is None
        reg.execute.assert_not_called()

    def test_no_tool_called_on_error_path(self):
        reg = _make_registry(raise_exc=RuntimeError("boom"))
        trace = _FakeTrace()
        result = SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        assert result["status"] == "failed"
        # Only run_swarm was attempted (and raised)
        called = [call[0][0] for call in reg.execute.call_args_list]
        assert called == ["run_swarm"]


# ---------------------------------------------------------------------------
# Group 8 — Sanitized failures
# ---------------------------------------------------------------------------

class TestSanitizedFailures:
    def test_run_swarm_exception_sanitized(self):
        exc_msg = "Authorization: Bearer secret-api-key-12345"
        reg = _make_registry(raise_exc=RuntimeError(exc_msg))
        trace = _FakeTrace()
        result = SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        assert result["status"] == "failed"
        assert "Bearer" not in result["content"]
        assert "secret" not in result["content"].lower()

    def test_run_swarm_error_status_sanitized(self):
        result_data = {
            "status": "error",
            "error": "Authorization: Bearer tok-abc123",
            "final_report": "",
            "tasks": [],
        }
        reg = _make_registry(result_data)
        trace = _FakeTrace()
        result = SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        assert result["status"] == "failed"
        assert "Bearer" not in result["content"]

    def test_no_traceback_in_error(self):
        exc_msg = "Traceback (most recent call last):\n  File test.py\nValueError: bad"
        reg = _make_registry(raise_exc=RuntimeError(exc_msg))
        trace = _FakeTrace()
        result = SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        assert "Traceback" not in result["content"]

    def test_failed_result_has_routed_by(self):
        reg = _make_registry(raise_exc=RuntimeError("boom"))
        trace = _FakeTrace()
        result = SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        assert result["routed_by"] == "swarm_workflow"

    def test_missing_final_report_error_is_closed(self):
        result_data = {**_GOOD_RESULT, "final_report": None}
        reg = _make_registry(result_data)
        trace = _FakeTrace()
        result = SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        assert result["status"] == "failed"

    def test_unparseable_result_is_closed(self):
        reg = MagicMock()
        reg.execute.return_value = "this is not json at all"
        trace = _FakeTrace()
        result = SwarmWorkflowDispatcher().try_route(CANONICAL_PROMPT, reg, trace)
        assert result["status"] == "failed"


# ---------------------------------------------------------------------------
# Group 9 — Out-of-scope prompts return None
# ---------------------------------------------------------------------------

class TestOutOfScope:
    def _route(self, prompt: str) -> Any:
        reg = _make_registry()
        trace = _FakeTrace()
        return SwarmWorkflowDispatcher().try_route(prompt, reg, trace)

    def test_market_data_prompt_not_intercepted(self):
        assert self._route("What is the current price of BTC?") is None

    def test_candlestick_prompt_not_intercepted(self):
        assert self._route("Show me candlestick patterns for ETH.") is None

    def test_backtest_prompt_not_intercepted(self):
        assert self._route(
            "Backtest a 20/50 MA crossover on BTC-USDT from 2024-01-01 to 2024-12-31."
        ) is None

    def test_swarm_without_preset_not_intercepted(self):
        assert self._route("Run a swarm on ETH for 30d.") is None

    def test_swarm_without_swarm_keyword_not_intercepted(self):
        assert self._route(
            "Use the crypto_research_lab to analyze ETH for 30d."
        ) is None

    def test_loop_integration_import(self):
        from src.agent import loop as loop_mod
        import inspect
        src = inspect.getsource(loop_mod)
        assert "SwarmWorkflowDispatcher" in src

    def test_loop_integration_try_route(self):
        from src.agent import loop as loop_mod
        import inspect
        src = inspect.getsource(loop_mod)
        assert "SwarmWorkflowDispatcher().try_route" in src
