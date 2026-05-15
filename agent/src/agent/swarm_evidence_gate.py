"""Swarm Evidence Quality Gate (Patch 15).

Evaluates whether a run_swarm result contains minimum evidence markers.
Does not validate factual correctness — only structural evidence presence.

Gate status:
  fail:    empty / whitespace final_report (hard fail)
  partial: no evidence keywords found across final_report + task summaries
  pass:    evidence keywords found

Advisory (does not change gate status):
  has_limitations_section: True/False
  warnings: ["no_limitations_section"] when limitation keywords are absent
"""
from __future__ import annotations

_EVIDENCE_KEYWORDS: frozenset[str] = frozenset({
    # Sentiment / direction
    "bullish", "bearish", "neutral", "positive", "negative", "momentum",
    # Positions / allocation
    "position", "allocation", "weight", "exposure",
    # Crypto assets
    "btc", "eth", "sol", "xrp", "bnb", "ada", "doge", "avax", "matic",
    # On-chain / DeFi metrics
    "on-chain", "onchain", "chain", "defi", "tvl", "liquidity",
    # Market data
    "price", "volume", "signal", "trend", "resistance", "support",
    # Analysis terms
    "analysis", "sentiment", "correlation", "alpha", "beta",
    "indicator", "metric", "data", "finding", "observation", "source",
    # Report structure terms
    "synthesis", "summary",
})

_LIMITATION_KEYWORDS: frozenset[str] = frozenset({
    "limitation", "caveat", "risk", "uncertainty", "disclaimer",
    "caution", "historical", "not guaranteed", "subject to",
    "research only", "simulation", "incomplete", "further",
    "note:", "note that", "important:", "warning:",
    "limitação", "ressalva", "risco", "incerteza",
})


class SwarmEvidenceQualityGate:
    """Minimum evidence gate for Swarm final reports.

    Call evaluate() after run_swarm succeeds and the report is non-empty.
    Integrate result into the dispatcher return value.
    """

    def evaluate(self, final_report: str, tasks: list) -> dict:
        if not final_report or not final_report.strip():
            return {
                "status": "fail",
                "reason": "final_report is empty",
                "has_evidence": False,
                "has_limitations_section": False,
                "warnings": [],
            }

        # Build corpus: final_report + all task summaries
        corpus = final_report.lower()
        for task in tasks:
            corpus += " " + (task.get("summary") or "").lower()

        has_evidence = any(kw in corpus for kw in _EVIDENCE_KEYWORDS)
        has_limitations = any(kw in final_report.lower() for kw in _LIMITATION_KEYWORDS)

        if not has_evidence:
            return {
                "status": "partial",
                "reason": "no evidence markers found in report or task summaries",
                "has_evidence": False,
                "has_limitations_section": has_limitations,
                "warnings": [] if has_limitations else ["no_limitations_section"],
            }

        warnings = [] if has_limitations else ["no_limitations_section"]
        return {
            "status": "pass",
            "reason": "",
            "has_evidence": True,
            "has_limitations_section": has_limitations,
            "warnings": warnings,
        }
