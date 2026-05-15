"""Tests for SwarmEvidenceQualityGate (Patch 15).

Covers gate logic in isolation and integration with SwarmWorkflowDispatcher.
Risk level: 3 (modifies dispatcher behaviour). RED/GREEN applied.

Gate contract:
  - fail:    empty/whitespace final_report
  - partial: no evidence keywords found across (final_report + task summaries)
  - pass:    evidence keywords found
  - warnings: ["no_limitations_section"] added to pass result when limitation
              keywords are absent (advisory; does not change gate status)
"""
from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest

_CANONICAL_PROMPT = "Run the crypto_research_lab swarm on ETH with timeframe 30d."

_RICH_REPORT = (
    "## Alpha Synthesis\n"
    "Bullish on ETH. Risk: historical data only. Core position: 60% BTC, 20% ETH.\n"
    "Limitation: backtest period does not include 2025 market regime.\n"
)
_BARE_REPORT = (
    "## Alpha Synthesis\n"
    "Bullish on ETH. Core position: 60% BTC, 20% ETH.\n"
)
_NO_EVIDENCE_REPORT = "The agents completed their work."
_GOOD_TASKS = [
    {"id": "t1", "agent_id": "onchain_analyst", "status": "completed", "summary": "On-chain: healthy."},
    {"id": "t2", "agent_id": "defi_analyst", "status": "completed", "summary": "DeFi: TVL growing."},
    {"id": "t3", "agent_id": "crypto_sentiment_analyst", "status": "completed", "summary": "Sentiment: neutral."},
    {"id": "t4", "agent_id": "alpha_synthesizer", "status": "completed", "summary": "Alpha: buy ETH."},
]
_GOOD_SWARM_RESULT = {
    "status": "completed",
    "run_id": "test-run-001",
    "preset": "crypto_research_lab",
    "auto_variables": {},
    "final_report": _BARE_REPORT,
    "tasks": _GOOD_TASKS,
    "token_usage": {},
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
        payload = json.dumps(result if result is not None else _GOOD_SWARM_RESULT)
        reg.execute.return_value = payload
    return reg


# ---------------------------------------------------------------------------
# Gate module — unit tests (isolated)
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_gate_fails_on_empty_report() -> None:
    from src.agent.swarm_evidence_gate import SwarmEvidenceQualityGate
    gate = SwarmEvidenceQualityGate()
    for empty in ("", "   ", "\n\t"):
        result = gate.evaluate(empty, _GOOD_TASKS)
        assert result["status"] == "fail", f"Empty report must fail gate: {empty!r}"


@pytest.mark.unit
def test_gate_partial_when_no_evidence_keywords() -> None:
    from src.agent.swarm_evidence_gate import SwarmEvidenceQualityGate
    gate = SwarmEvidenceQualityGate()
    result = gate.evaluate(_NO_EVIDENCE_REPORT, [])
    assert result["status"] == "partial", (
        "Report with no evidence keywords must yield partial"
    )
    assert result["has_evidence"] is False


@pytest.mark.unit
def test_gate_pass_with_warning_when_no_limitation_keywords() -> None:
    from src.agent.swarm_evidence_gate import SwarmEvidenceQualityGate
    gate = SwarmEvidenceQualityGate()
    result = gate.evaluate(_BARE_REPORT, _GOOD_TASKS)
    assert result["status"] == "pass", (
        "Report with evidence keywords must pass even without limitation section"
    )
    assert result["has_limitations_section"] is False
    assert "no_limitations_section" in result["warnings"]


@pytest.mark.unit
def test_gate_pass_clean_when_both_evidence_and_limitation_present() -> None:
    from src.agent.swarm_evidence_gate import SwarmEvidenceQualityGate
    gate = SwarmEvidenceQualityGate()
    result = gate.evaluate(_RICH_REPORT, _GOOD_TASKS)
    assert result["status"] == "pass"
    assert result["has_evidence"] is True
    assert result["has_limitations_section"] is True
    assert result["warnings"] == []


@pytest.mark.unit
def test_gate_partial_when_task_summaries_have_no_evidence_and_report_bare() -> None:
    """Even if all tasks completed, if report + summaries have no evidence → partial."""
    from src.agent.swarm_evidence_gate import SwarmEvidenceQualityGate
    gate = SwarmEvidenceQualityGate()
    bare_tasks = [
        {"id": "t1", "agent_id": "agent_a", "status": "completed", "summary": "Done."},
        {"id": "t2", "agent_id": "agent_b", "status": "completed", "summary": "Finished."},
    ]
    result = gate.evaluate(_NO_EVIDENCE_REPORT, bare_tasks)
    assert result["status"] == "partial"


@pytest.mark.unit
def test_gate_partial_for_json_like_text() -> None:
    """JSON-like tool call text has no evidence keywords → partial."""
    from src.agent.swarm_evidence_gate import SwarmEvidenceQualityGate
    gate = SwarmEvidenceQualityGate()
    fake_llm_text = (
        '{"function": "load_skill", "args": {"name": "crypto_research_lab"}};'
        ' {"function": "run_swarm", "args": {"prompt": "..."}}'
    )
    result = gate.evaluate(fake_llm_text, [])
    assert result["status"] in ("partial", "fail"), (
        "JSON-like LLM output must not pass evidence gate"
    )


# ---------------------------------------------------------------------------
# Integration — dispatcher + gate
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_dispatcher_success_when_gate_passes() -> None:
    from src.agent.swarm_workflow import SwarmWorkflowDispatcher
    reg = _make_registry(_GOOD_SWARM_RESULT)
    trace = _FakeTrace()
    result = SwarmWorkflowDispatcher().try_route(_CANONICAL_PROMPT, reg, trace)
    assert result is not None
    assert result["status"] == "success"
    assert result["routed_by"] == "swarm_workflow"
    assert result["iterations"] == 0


_BARE_TASKS = [
    {"id": "t1", "agent_id": "agent_a", "status": "completed", "summary": "Done."},
    {"id": "t2", "agent_id": "agent_b", "status": "completed", "summary": "Finished."},
]
_NO_EVIDENCE_RESULT = {
    **_GOOD_SWARM_RESULT,
    "final_report": _NO_EVIDENCE_REPORT,
    "tasks": _BARE_TASKS,
}


@pytest.mark.unit
def test_dispatcher_partial_when_gate_yields_partial() -> None:
    """Report + task summaries with no evidence keywords → gate partial → dispatcher partial."""
    from src.agent.swarm_workflow import SwarmWorkflowDispatcher
    reg = _make_registry(_NO_EVIDENCE_RESULT)
    trace = _FakeTrace()
    result = SwarmWorkflowDispatcher().try_route(_CANONICAL_PROMPT, reg, trace)
    assert result is not None
    assert result["status"] == "partial", (
        "Dispatcher must return partial when evidence gate yields partial"
    )
    assert result["routed_by"] == "swarm_workflow"
    assert result["status"] != "success", (
        "Silent success is forbidden when evidence gate finds no evidence"
    )


@pytest.mark.unit
def test_no_llm_fallback_on_gate_partial() -> None:
    """Dispatcher must return a dict (not None) when gate is partial — None would
    cause loop.py to fall through to the ReAct LLM loop."""
    from src.agent.swarm_workflow import SwarmWorkflowDispatcher
    reg = _make_registry(_NO_EVIDENCE_RESULT)
    trace = _FakeTrace()
    result = SwarmWorkflowDispatcher().try_route(_CANONICAL_PROMPT, reg, trace)
    assert result is not None, "Dispatcher must never return None — that triggers LLM fallback"
    called = [call[0][0] for call in reg.execute.call_args_list]
    assert called == ["run_swarm"], f"Only run_swarm may be called; got: {called}"
