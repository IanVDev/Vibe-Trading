"""Anti-drift canary for docs/PROJECT_STATE_V0_1.md.

Risk level: 2. Ensures the project state snapshot remains accurate — lists all
four SEALED levels, acknowledges the Evidence Quality Gate, retains safety
prohibitions, and does not overstate project maturity. Not a SEALED baseline;
no RED/GREEN required.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOC = _REPO_ROOT / "docs" / "PROJECT_STATE_V0_1.md"


@pytest.mark.unit
def test_project_state_doc_exists() -> None:
    assert _DOC.is_file(), (
        f"Project state doc missing at {_DOC}. Run Patch 16 to create it."
    )


@pytest.mark.unit
def test_doc_mentions_all_four_sealed_levels() -> None:
    text = _DOC.read_text(encoding="utf-8")
    for marker in ("N1", "N2", "N3", "N4"):
        assert marker in text, (
            f"Project state doc must mention SEALED level {marker!r}."
        )
    assert "SEALED" in text, "Project state doc must mention SEALED status."


@pytest.mark.unit
def test_doc_mentions_evidence_quality_gate_enabled() -> None:
    text = _DOC.read_text(encoding="utf-8")
    lower = text.lower()
    assert "evidence quality gate" in lower or "swarmevidence" in lower or "evidence_quality_gate" in lower, (
        "Project state doc must mention the Evidence Quality Gate."
    )
    assert "enabled" in lower or "active" in lower or "pass" in lower, (
        "Project state doc must confirm the gate is enabled/active."
    )


@pytest.mark.unit
def test_doc_prohibits_real_trading_and_financial_advice() -> None:
    text = _DOC.read_text(encoding="utf-8")
    lower = text.lower()
    assert "no live trading" in lower or "live trading" in lower or "no orders" in lower or "not a trading system" in lower, (
        "Doc must explicitly disclaim live trading."
    )
    assert "investment advice" in lower or "financial advisor" in lower or "not investment" in lower, (
        "Doc must disclaim investment/financial advice."
    )
    assert "profit" in lower or "lucro" in lower, (
        "Doc must address profit claims."
    )


@pytest.mark.unit
def test_doc_differentiates_backtest_from_real_trading() -> None:
    text = _DOC.read_text(encoding="utf-8")
    lower = text.lower()
    assert "backtest" in lower, "Doc must mention backtest."
    assert "historical" in lower, "Doc must clarify backtest is historical."
    assert "simulation" in lower or "simulate" in lower, (
        "Doc must use 'simulation' to distinguish backtest from live trading."
    )


@pytest.mark.unit
def test_doc_differentiates_evidence_gate_from_factual_accuracy() -> None:
    text = _DOC.read_text(encoding="utf-8")
    lower = text.lower()
    gate_present = "evidence gate" in lower or "quality gate" in lower or "swarmevidence" in lower
    assert gate_present, "Doc must mention the evidence gate."
    structural_markers = (
        "structural",
        "keyword",
        "not audited",
        "does not verify",
        "not a quality audit",
        "minimum bar",
        "factual accuracy",
    )
    found = any(m in lower for m in structural_markers)
    assert found, (
        "Doc must clarify that the evidence gate is structural/keyword-based, "
        "not a factual accuracy audit."
    )


@pytest.mark.unit
def test_doc_does_not_overstate_maturity() -> None:
    text = _DOC.read_text(encoding="utf-8")
    lower = text.lower()
    forbidden = (
        "production ready",
        "production-ready",
        "fully verified",
        "guaranteed accuracy",
        "guarantees future",
        "proven strategy",
        "fully tested in production",
    )
    found = [f for f in forbidden if f in lower]
    assert not found, (
        f"Project state doc must not overstate maturity. Found: {found}"
    )
