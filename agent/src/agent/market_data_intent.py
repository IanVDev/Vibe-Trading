"""Deterministic detector for simple market-data prompts.

Runs before the LLM/ReAct loop. If a prompt clearly asks for price/OHLCV on
a known symbol AND does not look like a strategy/backtest/analysis request,
returns a MarketDataIntent that the dispatcher uses to call get_market_data
directly. Otherwise returns None and the agent loop proceeds as before.

Failure mode covered: small LLMs (qwen2.5:7b) emit empty content on vague
PT-BR prompts even with explicit system prompt policy. This module removes
the LLM from the decision for the simple case.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from src.tools.market_data_tool import _normalize_symbol

_INTENT_WORDS = (
    "price", "preço", "preco", "cotação", "cotacao",
    "ohlcv", "candle", "candles",
    "fechamento", "close", "closing",
    "volume", "ticker",
    "dias", "days",
    "current", "atual", "now",
)

_BLACKLIST_TOKENS = (
    "backtest",
    "strategy",
    "estratégia", "estrategia",
    "candlestick pattern", "candlestick patterns",
    "padrões de candle", "padrao de candle",
    "analyze", "analise", "análise técnica", "analise tecnica",
    "swarm",
    "signal_engine", "signal engine",
    "optimize", "otimizar",
    "moving average", "média móvel", "media movel",
    "RSI", "MACD",
)

_LIMIT_RE = re.compile(r"\b(\d{1,3})\s*(?:days?|dias?)\b", re.IGNORECASE)

_TIMEFRAME_HOUR_RE = re.compile(r"\b(?:hour(?:ly)?|hora|horár)", re.IGNORECASE)
_TIMEFRAME_15M_RE = re.compile(r"\b(?:15\s*-?\s*(?:m|min|minute|minutos?))\b", re.IGNORECASE)
_TIMEFRAME_DAY_RE = re.compile(r"\b(?:daily|diári|day|dia\b)", re.IGNORECASE)

_CURRENT_PRICE_RE = re.compile(
    r"\b(?:current|atual|now|agora|price|preço|preco|cotação|cotacao)\b",
    re.IGNORECASE,
)

_SPECIFIC_SYMBOL_RES = (
    re.compile(r"\b([A-Z]{2,5}[\-/](?:USDT|USD|BTC|ETH|BUSD|USDC))\b", re.IGNORECASE),
    re.compile(r"\b([A-Z]{2,5}(?:USDT|USD|BTC|ETH|BUSD|USDC))\b", re.IGNORECASE),
    re.compile(r"\b(\d{4,6}\.(?:HK|SH|SS|SZ))\b", re.IGNORECASE),
    re.compile(r"\b([A-Z]{1,5}\.(?:HK|SH|SS|SZ))\b", re.IGNORECASE),
)
_PLAIN_TICKER_RE = re.compile(r"\b([A-Z]{2,5})\b")


@dataclass(frozen=True)
class MarketDataIntent:
    """Structured result of a successful market-data intent detection."""

    symbol: str
    timeframe: str
    limit: int
    include_current_price: bool


_PLAIN_TICKER_BLOCKLIST = {
    # PT-BR common words that match A-Z but are not tickers
    "OBTENHA", "MOSTRE", "PRECO", "FECHAMENTO", "DIAS", "TABELA",
    "COMO", "UMA", "ATUAL", "DO", "DA", "DOS", "DAS", "PARA",
    # EN common words/abbreviations
    "GET", "THE", "AND", "FOR", "WITH", "FROM", "PRICE", "CLOSE",
    "OPEN", "HIGH", "LOW", "VOLUME", "LAST", "DAYS", "CURRENT",
    "TICKER", "STOCK", "CANDLE", "CANDLES", "OHLCV", "DATA",
}


def _extract_symbol(prompt: str) -> Optional[str]:
    """Find a market symbol in the prompt.

    Strategy: try specific patterns first (crypto pair, HK/A-share suffix).
    Only fall back to plain 2-5 letter tickers if (a) the token is in the
    original prompt in uppercase (filters PT-BR words like "Obtenha") and
    (b) the token is not in the blocklist of common English/PT-BR words.
    """
    for pattern in _SPECIFIC_SYMBOL_RES:
        match = pattern.search(prompt)
        if match:
            canonical, _provider = _normalize_symbol(match.group(1))
            if canonical is not None:
                return canonical

    for match in _PLAIN_TICKER_RE.finditer(prompt):
        token = match.group(1)
        if token in _PLAIN_TICKER_BLOCKLIST:
            continue
        canonical, _provider = _normalize_symbol(token)
        if canonical is not None:
            return canonical

    return None


def _extract_limit(prompt: str) -> int:
    m = _LIMIT_RE.search(prompt)
    if m:
        return min(int(m.group(1)), 100)
    return 7


def _extract_timeframe(prompt: str) -> str:
    if _TIMEFRAME_15M_RE.search(prompt):
        return "15m"
    if _TIMEFRAME_HOUR_RE.search(prompt):
        return "1h"
    if _TIMEFRAME_DAY_RE.search(prompt):
        return "1d"
    return "1d"


def _has_intent_word(prompt_lower: str) -> bool:
    return any(w in prompt_lower for w in _INTENT_WORDS)


def _matches_blacklist(prompt_lower: str) -> bool:
    return any(token in prompt_lower for token in _BLACKLIST_TOKENS)


def detect_market_data_intent(prompt: str) -> Optional[MarketDataIntent]:
    """Return a MarketDataIntent if prompt unambiguously asks for market data.

    Three AND conditions, no scoring, no thresholds.
    """
    if not prompt or not isinstance(prompt, str):
        return None

    prompt_lower = prompt.lower()

    if _matches_blacklist(prompt_lower):
        return None
    if not _has_intent_word(prompt_lower):
        return None

    canonical = _extract_symbol(prompt)
    if canonical is None:
        return None

    return MarketDataIntent(
        symbol=canonical,
        timeframe=_extract_timeframe(prompt),
        limit=_extract_limit(prompt),
        include_current_price=bool(_CURRENT_PRICE_RE.search(prompt)),
    )
