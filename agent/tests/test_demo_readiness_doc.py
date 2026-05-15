"""Anti-drift canary for docs/DEMO_READINESS_CHECKLIST.md.

Risk level: 2. Ensures the demo checklist remains coherent — covers all four
SEALED levels, retains safety prohibitions, and keeps PASS/FAIL criteria
visible. Not a SEALED baseline; no RED/GREEN required.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CHECKLIST = _REPO_ROOT / "docs" / "DEMO_READINESS_CHECKLIST.md"
_BEGINNER_TRAIL = _REPO_ROOT / "docs" / "BEGINNER_TRAIL.md"


@pytest.mark.unit
def test_demo_checklist_exists() -> None:
    assert _CHECKLIST.is_file(), (
        f"Demo readiness checklist missing at {_CHECKLIST}. "
        "Run Patch 12 to create it."
    )


@pytest.mark.unit
def test_checklist_mentions_all_four_levels() -> None:
    text = _CHECKLIST.read_text(encoding="utf-8")
    for marker in (
        "Level 1",
        "Level 2",
        "Level 3",
        "Level 4",
    ):
        assert marker in text, (
            f"Checklist does not mention {marker!r} — all four SEALED levels must be covered."
        )


@pytest.mark.unit
def test_checklist_prohibits_real_trading() -> None:
    text = _CHECKLIST.read_text(encoding="utf-8")
    assert "real order" in text.lower() or "real trading" in text.lower() or "live order" in text.lower() or "live trading" in text.lower(), (
        "Checklist must explicitly prohibit real or live trading/orders."
    )


@pytest.mark.unit
def test_checklist_prohibits_profit_and_financial_advice() -> None:
    text = _CHECKLIST.read_text(encoding="utf-8")
    assert "profitability" in text.lower() or "profit" in text.lower(), (
        "Checklist must address profit/profitability claims."
    )
    assert "financial advice" in text.lower() or "investment advice" in text.lower(), (
        "Checklist must prohibit financial or investment advice."
    )


@pytest.mark.unit
def test_checklist_contains_pass_fail_criteria() -> None:
    text = _CHECKLIST.read_text(encoding="utf-8")
    assert "PASS" in text and "FAIL" in text, (
        "Checklist must contain explicit PASS/FAIL criteria."
    )


@pytest.mark.unit
def test_checklist_acknowledges_swarm_factual_risk() -> None:
    text = _CHECKLIST.read_text(encoding="utf-8")
    swarm_risk_markers = (
        "factual accuracy",
        "factually verified",
        "factual correctness",
        "content quality",
        "does not verify",
    )
    found = any(m in text.lower() for m in swarm_risk_markers)
    assert found, (
        "Checklist must acknowledge the residual factual risk of Swarm agent outputs."
    )


@pytest.mark.unit
def test_beginner_trail_references_checklist() -> None:
    text = _BEGINNER_TRAIL.read_text(encoding="utf-8")
    assert "DEMO_READINESS_CHECKLIST" in text or "demo readiness" in text.lower() or "demo checklist" in text.lower(), (
        "BEGINNER_TRAIL.md must reference the Demo Readiness Checklist."
    )
