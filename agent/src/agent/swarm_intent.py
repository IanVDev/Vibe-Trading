"""Deterministic detector for named-preset swarm prompts (Patch 9)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# All preset names from SwarmTool._PRESET_KEYWORDS — kept in sync manually.
_ALLOWED_PRESETS: frozenset[str] = frozenset({
    "global_allocation_committee",
    "risk_committee",
    "quant_strategy_desk",
    "equity_research_team",
    "factor_research_committee",
    "event_driven_task_force",
    "etf_allocation_desk",
    "derivatives_strategy_desk",
    "crypto_research_lab",
    "credit_research_team",
    "convertible_bond_team",
    "fundamental_research_team",
    "commodity_research_team",
    "fund_selection_panel",
    "social_alpha_team",
    "geopolitical_war_room",
    "pairs_research_lab",
    "investment_committee",
    "macro_strategy_forum",
    "statistical_arbitrage_desk",
    "sentiment_intelligence_team",
    "technical_analysis_panel",
    "sector_rotation_team",
    "portfolio_review_board",
    "ml_quant_lab",
})

_SWARM_WORDS = ("swarm",)

_TARGET_RE = re.compile(
    r"\b(BTC|ETH|SOL|XRP|USDT|BNB|ADA|DOGE|AVAX|MATIC|DOT|LINK|UNI|ATOM|LTC)\b",
    re.IGNORECASE,
)

_TIMEFRAME_RE = re.compile(
    r"\b(\d+\s*[dwmqy]|short[- ]term|medium[- ]term|long[- ]term|intraday)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SwarmIntent:
    preset_name: str
    target: str
    timeframe: str


def _extract_preset(prompt_lower: str) -> Optional[str]:
    for name in _ALLOWED_PRESETS:
        if name in prompt_lower:
            return name
    return None


def _extract_target(prompt: str) -> str:
    m = _TARGET_RE.search(prompt)
    if m:
        return m.group(1).upper()
    return "unspecified"


def _extract_timeframe(prompt: str) -> str:
    m = _TIMEFRAME_RE.search(prompt)
    if m:
        return m.group(1).strip()
    return "medium-term"


def detect_swarm_intent(prompt: str) -> Optional[SwarmIntent]:
    if not prompt or not isinstance(prompt, str):
        return None
    prompt_lower = prompt.lower()
    if not any(w in prompt_lower for w in _SWARM_WORDS):
        return None
    preset_name = _extract_preset(prompt_lower)
    if preset_name is None:
        return None
    target = _extract_target(prompt)
    timeframe = _extract_timeframe(prompt)
    return SwarmIntent(
        preset_name=preset_name,
        target=target,
        timeframe=timeframe,
    )
