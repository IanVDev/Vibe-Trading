"""Anti-drift canary for the Beginner Trail status document.

Risk level: 2 (doc anti-drift). Does NOT protect a runtime contract —
only guards against accidental deletion or misrepresentation of the trail
status in docs/BEGINNER_TRAIL.md.

Six lightweight checks:
  1. Document exists.
  2. All four SEALED levels are mentioned.
  3. Disclaimer: not real trading.
  4. Residual risk: factual accuracy of Swarm agents is not guaranteed.
  5. No guarantee of profit or future returns.
  6. README references the trail.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_TRAIL_DOC = _REPO_ROOT / "docs" / "BEGINNER_TRAIL.md"
_README = _REPO_ROOT / "README.md"


@pytest.mark.unit
def test_trail_doc_exists() -> None:
    assert _TRAIL_DOC.is_file(), (
        f"Beginner trail doc missing at {_TRAIL_DOC}."
    )


@pytest.mark.unit
def test_trail_doc_mentions_all_four_sealed_levels() -> None:
    text = _TRAIL_DOC.read_text(encoding="utf-8")
    for level_marker in (
        "Level 1",
        "Level 2",
        "Level 3",
        "Level 4",
        "SEALED",
    ):
        assert level_marker in text, (
            f"Trail doc must mention {level_marker!r} — drift detected."
        )


@pytest.mark.unit
def test_trail_doc_contains_no_real_trading_disclaimer() -> None:
    text = _TRAIL_DOC.read_text(encoding="utf-8")
    assert "does not execute" in text or "not execute live trades" in text, (
        "Trail doc must state that the system does not execute live trades."
    )
    assert "not investment advice" in text or "not financial advice" in text or "not a guarantee" in text, (
        "Trail doc must contain a disclaimer phrase."
    )


@pytest.mark.unit
def test_trail_doc_acknowledges_swarm_factual_risk() -> None:
    text = _TRAIL_DOC.read_text(encoding="utf-8")
    assert "factual" in text.lower(), (
        "Trail doc must acknowledge the factual-correctness residual risk for Swarm agents."
    )


@pytest.mark.unit
def test_trail_doc_does_not_guarantee_profit() -> None:
    text = _TRAIL_DOC.read_text(encoding="utf-8").lower()
    assert "past performance" in text or "future results" in text, (
        "Trail doc must include a 'past performance / future results' disclaimer."
    )
    profit_guarantee_phrases = (
        "guaranteed profit",
        "guaranteed return",
        "guaranteed to profit",
        "guaranteed to make money",
    )
    for phrase in profit_guarantee_phrases:
        assert phrase not in text, (
            f"Trail doc must not contain profit guarantee phrase: {phrase!r}"
        )


@pytest.mark.unit
def test_readme_references_beginner_trail() -> None:
    text = _README.read_text(encoding="utf-8")
    assert "Beginner Trail" in text, (
        "README.md must contain a 'Beginner Trail' section or reference."
    )
    assert "BEGINNER_TRAIL.md" in text or "beginner_trail" in text.lower(), (
        "README.md must link to the BEGINNER_TRAIL.md document."
    )
