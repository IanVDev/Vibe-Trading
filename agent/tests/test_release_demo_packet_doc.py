"""Anti-drift canary for docs/RELEASE_DEMO_PACKET_V0_1.md.

Risk level: 2. Ensures the release demo packet remains accurate and safe —
covers all four SEALED levels, links to the three supporting runbooks, retains
safety prohibitions, acknowledges Swarm factual risk, and contains both pre-demo
and post-demo checklists. Not a SEALED baseline; no RED/GREEN required.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PACKET = _REPO_ROOT / "docs" / "RELEASE_DEMO_PACKET_V0_1.md"


@pytest.mark.unit
def test_release_packet_exists() -> None:
    assert _PACKET.is_file(), (
        f"Release demo packet missing at {_PACKET}. Run Patch 14 to create it."
    )


@pytest.mark.unit
def test_packet_mentions_all_four_levels() -> None:
    text = _PACKET.read_text(encoding="utf-8")
    for marker in ("Level 1", "Level 2", "Level 3", "Level 4"):
        assert marker in text, (
            f"Release packet must mention {marker!r} — all four SEALED levels must be covered."
        )


@pytest.mark.unit
def test_packet_links_supporting_docs() -> None:
    text = _PACKET.read_text(encoding="utf-8")
    for doc in ("BEGINNER_TRAIL", "DEMO_READINESS_CHECKLIST", "LOCAL_GATE_RUNBOOK"):
        assert doc in text, (
            f"Release packet must link to {doc}.md."
        )


@pytest.mark.unit
def test_packet_prohibits_real_trading_and_financial_advice() -> None:
    text = _PACKET.read_text(encoding="utf-8")
    lower = text.lower()
    assert "trading real" in lower or "real trading" in lower or "live trading" in lower or "not a trading system" in lower or "no orders" in lower or "no live trading" in lower, (
        "Packet must explicitly prohibit or disclaim real/live trading."
    )
    assert "financial advice" in lower or "investment advice" in lower, (
        "Packet must prohibit financial or investment advice."
    )
    assert "profit" in lower or "lucro" in lower, (
        "Packet must address profit claims."
    )


@pytest.mark.unit
def test_packet_acknowledges_swarm_factual_risk() -> None:
    text = _PACKET.read_text(encoding="utf-8")
    lower = text.lower()
    markers = (
        "factual accuracy",
        "factually accurate",
        "factual risk",
        "not audited",
        "does not audit",
        "content quality",
        "factualidade",
    )
    assert any(m in lower for m in markers), (
        "Packet must acknowledge the residual factual risk of Swarm agent outputs."
    )


@pytest.mark.unit
def test_packet_contains_pre_and_post_demo_checklists() -> None:
    text = _PACKET.read_text(encoding="utf-8")
    lower = text.lower()
    assert "pre-demo" in lower or "pré-demo" in lower or "pre demo" in lower, (
        "Packet must contain a pre-demo checklist."
    )
    assert "post-demo" in lower or "pós-demo" in lower or "post demo" in lower, (
        "Packet must contain a post-demo checklist."
    )


@pytest.mark.unit
def test_packet_does_not_promise_future_performance() -> None:
    text = _PACKET.read_text(encoding="utf-8")
    lower = text.lower()
    forbidden = (
        "guarantees future",
        "predicts future returns",
        "future returns guaranteed",
        "will be profitable",
        "guaranteed profit",
        "guaranteed return",
    )
    found = [f for f in forbidden if f in lower]
    assert not found, (
        f"Packet must not contain promises of future performance. Found: {found}"
    )
