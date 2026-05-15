"""Anti-drift canary for docs/LOCAL_GATE_RUNBOOK.md.

Risk level: 2. Ensures the local gate runbook remains coherent — declares that
GitHub Actions are not currently required, defines local gates, references the
SEALED canaries, the smoke process, the PR-FLOW format, and prohibits faking
gate execution. Not a SEALED baseline; no RED/GREEN required.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_RUNBOOK = _REPO_ROOT / "docs" / "LOCAL_GATE_RUNBOOK.md"


@pytest.mark.unit
def test_runbook_exists() -> None:
    assert _RUNBOOK.is_file(), (
        f"Local gate runbook missing at {_RUNBOOK}. Run Patch 13 to create it."
    )


@pytest.mark.unit
def test_runbook_states_github_actions_disabled() -> None:
    text = _RUNBOOK.read_text(encoding="utf-8")
    markers = (
        "github actions",
        "github actions are disabled",
        "not configured",
        "not required",
        "disabled",
    )
    lower = text.lower()
    found = any(m in lower for m in markers)
    assert found, (
        "Runbook must state that GitHub Actions are not currently required/configured."
    )


@pytest.mark.unit
def test_runbook_defines_local_gates() -> None:
    text = _RUNBOOK.read_text(encoding="utf-8")
    lower = text.lower()
    assert "local gate" in lower or "gates locais" in lower or "mandatory gates" in lower or "gate map" in lower, (
        "Runbook must define local gates (gate map or mandatory gates section)."
    )


@pytest.mark.unit
def test_runbook_mentions_sealed_canaries() -> None:
    text = _RUNBOOK.read_text(encoding="utf-8")
    assert "SEALED" in text, (
        "Runbook must mention SEALED canaries."
    )
    for level in ("N1", "N2", "N3", "N4"):
        assert level in text, f"Runbook must reference SEALED canary {level}."


@pytest.mark.unit
def test_runbook_mentions_manual_smoke() -> None:
    text = _RUNBOOK.read_text(encoding="utf-8")
    lower = text.lower()
    assert "smoke" in lower, (
        "Runbook must describe when to run a manual smoke test."
    )


@pytest.mark.unit
def test_runbook_defines_pr_flow_evidence_format() -> None:
    text = _RUNBOOK.read_text(encoding="utf-8")
    assert "PR-FLOW" in text or "pr-flow" in text.lower(), (
        "Runbook must define the mandatory PR-FLOW evidence format."
    )
    assert "Evidência" in text or "Evidence" in text or "evidence" in text.lower(), (
        "Runbook must include the evidence block in its PR-FLOW format."
    )


@pytest.mark.unit
def test_runbook_prohibits_faking_execution() -> None:
    text = _RUNBOOK.read_text(encoding="utf-8")
    lower = text.lower()
    forbidden_markers = (
        "fingir",
        "faking",
        "fake execution",
        "never mark",
        "never report",
        "proibido",
        "prohibited",
        "hard policy violation",
    )
    found = any(m in lower for m in forbidden_markers)
    assert found, (
        "Runbook must explicitly prohibit faking gate execution results."
    )
