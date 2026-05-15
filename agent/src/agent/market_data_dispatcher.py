"""Deterministic pre-LLM dispatcher for simple market-data prompts.

Sits between AgentLoop.run() and the ReAct while-loop. If the user prompt
matches MarketDataIntent (see market_data_intent.detect_market_data_intent),
this module calls get_market_data through the registry, formats the result
as a markdown table in pure Python, emits trace events, and returns a
short-circuit response. The LLM is never invoked.

Fail-closed:
- Tool returns status=error -> dispatcher returns sanitized failure;
  it never falls back to web_search, never invokes the LLM, never retries.
- Tool returns status=ok -> dispatcher renders a markdown table from the
  candles array.
- Logs are sanitized: no raw exception text, no user prompt content,
  no full URLs.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from src.agent.market_data_intent import (
    MarketDataIntent,
    detect_market_data_intent,
)

logger = logging.getLogger(__name__)

_LEAK_PATTERNS = (
    re.compile(r"authorization\s*:\s*\S+", re.IGNORECASE),
    re.compile(r"bearer\s+\S+", re.IGNORECASE),
    re.compile(r"\btoken\s*=\s*\S+", re.IGNORECASE),
    re.compile(r"\bapi[_-]?key\s*=\s*\S+", re.IGNORECASE),
    re.compile(r"\bsecret[-_]?[a-z0-9]+", re.IGNORECASE),
    re.compile(r"traceback[\s\S]*", re.IGNORECASE),
    re.compile(r"internal://\S+", re.IGNORECASE),
    re.compile(r"/Users/\S+", re.IGNORECASE),
    re.compile(r"/home/\S+", re.IGNORECASE),
    re.compile(r"proxy\.local:\d+", re.IGNORECASE),
)


def _sanitize(text: str) -> str:
    """Remove leak-prone substrings; preserve a short technical hint only."""
    cleaned = text or ""
    for pat in _LEAK_PATTERNS:
        cleaned = pat.sub("[redacted]", cleaned)
    return cleaned[:400]


def _format_markdown_table(payload: Dict[str, Any], intent: MarketDataIntent) -> str:
    """Render the tool JSON as a markdown table. Pure Python, deterministic."""
    symbol = payload.get("symbol") or intent.symbol
    provider = payload.get("provider", "unknown")
    timeframe = payload.get("timeframe", intent.timeframe)
    current_price = payload.get("current_price")
    candles: List[Dict[str, Any]] = payload.get("candles", []) or []

    lines: List[str] = []
    lines.append(f"**{symbol}** — provider: `{provider}` — timeframe: `{timeframe}`")
    if current_price is not None and intent.include_current_price:
        lines.append(f"Current price: **{current_price}**")
    lines.append("")
    lines.append("| Date | Open | High | Low | Close | Volume |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for c in candles:
        lines.append(
            f"| {c.get('date','?')} | {c.get('open','?')} | {c.get('high','?')} | "
            f"{c.get('low','?')} | {c.get('close','?')} | {c.get('volume','?')} |"
        )
    return "\n".join(lines)


class MarketDataDispatcher:
    """Routes simple market-data prompts directly to get_market_data."""

    ROUTED_BY = "market_data_router"

    def try_route(
        self,
        user_message: str,
        registry: Any,
        trace: Any,
    ) -> Optional[Dict[str, Any]]:
        """Attempt to handle the prompt deterministically.

        Returns:
            A short-circuit result dict (caller should return it immediately
            from AgentLoop.run) or None if the prompt should go through the
            normal ReAct loop.
        """
        intent = detect_market_data_intent(user_message)
        if intent is None:
            logger.debug("intent_skip reason=no_intent_or_blacklist")
            return None

        logger.info(
            "intent_detected symbol=%s timeframe=%s limit=%d",
            intent.symbol, intent.timeframe, intent.limit,
        )

        trace.write({
            "type": "router",
            "name": self.ROUTED_BY,
            "intent": {
                "symbol": intent.symbol,
                "timeframe": intent.timeframe,
                "limit": intent.limit,
                "include_current_price": intent.include_current_price,
            },
        })

        tool_args = {
            "symbol": intent.symbol,
            "timeframe": intent.timeframe,
            "limit": intent.limit,
        }
        trace.write({
            "type": "tool_call",
            "name": "get_market_data",
            "arguments": tool_args,
            "iter": 0,
        })

        try:
            raw = registry.execute("get_market_data", tool_args)
        except Exception:
            logger.warning("router_tool_invoke_failed")
            return self._fail(trace, "market data dispatch failed.")

        try:
            payload = json.loads(raw) if isinstance(raw, str) else dict(raw)
        except Exception:
            logger.warning("router_tool_response_not_json")
            return self._fail(trace, "market data response was not valid JSON.")

        trace.write({
            "type": "tool_result",
            "name": "get_market_data",
            "status": payload.get("status", "unknown"),
        })

        if payload.get("status") != "ok":
            raw_error = payload.get("error", "market data unavailable.")
            safe = _sanitize(str(raw_error))
            return self._fail(trace, f"market data error: {safe}")

        content = _format_markdown_table(payload, intent)
        trace.write({"type": "answer", "iter": 0, "content": content[:2000]})
        trace.write({
            "type": "end",
            "status": "success",
            "iterations": 0,
            "routed_by": self.ROUTED_BY,
        })

        return {
            "status": "success",
            "content": content,
            "iterations": 0,
            "routed_by": self.ROUTED_BY,
        }

    def _fail(self, trace: Any, message: str) -> Dict[str, Any]:
        safe = _sanitize(message)
        trace.write({"type": "answer", "iter": 0, "content": safe})
        trace.write({
            "type": "end",
            "status": "failed",
            "iterations": 0,
            "routed_by": self.ROUTED_BY,
        })
        return {
            "status": "failed",
            "content": safe,
            "iterations": 0,
            "routed_by": self.ROUTED_BY,
        }
