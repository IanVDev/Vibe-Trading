"""Unit tests for detect_market_data_intent — the deterministic pre-LLM detector.

Risk level 3: this detector decides whether a prompt short-circuits the ReAct
loop. False positives intercept prompts that should go through the LLM (bad);
false negatives are safe (prompt falls through to LLM as before).
"""

from __future__ import annotations

import pytest


# --- POSITIVE: must detect ---------------------------------------------------

@pytest.mark.unit
def test_detects_btc_usdt_pt_br_vague_canonical() -> None:
    """The exact prompt from the original briefing — primary acceptance case."""
    from src.agent.market_data_intent import detect_market_data_intent

    intent = detect_market_data_intent(
        "Obtenha o preço atual do BTC-USDT e os últimos 7 dias de "
        "fechamento diário. Mostre como uma tabela."
    )
    assert intent is not None
    assert intent.symbol in ("BTC-USDT", "BTC/USDT")
    assert intent.timeframe == "1d"
    assert intent.limit == 7
    assert intent.include_current_price is True


@pytest.mark.unit
def test_detects_eth_en_30_days() -> None:
    from src.agent.market_data_intent import detect_market_data_intent

    intent = detect_market_data_intent(
        "Get the current price of ETH-USDT and last 30 days closing prices."
    )
    assert intent is not None
    assert intent.symbol in ("ETH-USDT", "ETH/USDT")
    assert intent.timeframe == "1d"
    assert intent.limit == 30


@pytest.mark.unit
def test_detects_aapl_us_5_days() -> None:
    from src.agent.market_data_intent import detect_market_data_intent

    intent = detect_market_data_intent("AAPL stock price last 5 days close")
    assert intent is not None
    assert intent.symbol == "AAPL"
    assert intent.limit == 5


@pytest.mark.unit
def test_detects_hk_stock_pt_br() -> None:
    from src.agent.market_data_intent import detect_market_data_intent

    intent = detect_market_data_intent(
        "preço de fechamento do 0700.HK nos últimos 10 dias"
    )
    assert intent is not None
    assert intent.symbol == "0700.HK"
    assert intent.limit == 10


@pytest.mark.unit
@pytest.mark.parametrize("phrase,expected", [
    ("últimos 3 dias", 3),
    ("last 7 days", 7),
    ("last 30 days", 30),
    ("últimos 100 dias", 100),
])
def test_extracts_limit_variants(phrase: str, expected: int) -> None:
    from src.agent.market_data_intent import detect_market_data_intent

    intent = detect_market_data_intent(f"BTC-USDT price {phrase}")
    assert intent is not None
    assert intent.limit == expected


@pytest.mark.unit
def test_extracts_timeframe_hourly_pt() -> None:
    from src.agent.market_data_intent import detect_market_data_intent

    intent = detect_market_data_intent("BTC-USDT preço última hora horário")
    assert intent is not None
    assert intent.timeframe == "1h"


@pytest.mark.unit
def test_default_limit_when_absent() -> None:
    from src.agent.market_data_intent import detect_market_data_intent

    intent = detect_market_data_intent("BTC-USDT preço atual")
    assert intent is not None
    assert intent.limit == 7


@pytest.mark.unit
def test_default_timeframe_when_absent() -> None:
    from src.agent.market_data_intent import detect_market_data_intent

    intent = detect_market_data_intent("BTC-USDT preço")
    assert intent is not None
    assert intent.timeframe == "1d"


@pytest.mark.unit
def test_limit_capped_at_100() -> None:
    from src.agent.market_data_intent import detect_market_data_intent

    intent = detect_market_data_intent("BTC-USDT price last 999 days close")
    assert intent is not None
    assert intent.limit <= 100


# --- NEGATIVE: must NOT detect (blacklist or no symbol) ----------------------

@pytest.mark.unit
def test_does_not_intercept_backtest() -> None:
    from src.agent.market_data_intent import detect_market_data_intent

    assert detect_market_data_intent(
        "Backtest a BTC-USDT 20/50 moving-average strategy for 2024"
    ) is None


@pytest.mark.unit
def test_does_not_intercept_candlestick_pattern() -> None:
    from src.agent.market_data_intent import detect_market_data_intent

    assert detect_market_data_intent(
        "Identify candlestick patterns on BTC-USDT last 60 days"
    ) is None


@pytest.mark.unit
def test_does_not_intercept_strategy_pt_br() -> None:
    from src.agent.market_data_intent import detect_market_data_intent

    assert detect_market_data_intent(
        "Quero uma estratégia para BTC-USDT com média móvel"
    ) is None


@pytest.mark.unit
def test_does_not_intercept_swarm() -> None:
    from src.agent.market_data_intent import detect_market_data_intent

    assert detect_market_data_intent(
        "Run the crypto_research_lab swarm on ETH timeframe 30d"
    ) is None


@pytest.mark.unit
def test_does_not_intercept_analyze() -> None:
    from src.agent.market_data_intent import detect_market_data_intent

    assert detect_market_data_intent(
        "Analyze BTC-USDT fundamentals and risk"
    ) is None


@pytest.mark.unit
def test_does_not_intercept_without_symbol() -> None:
    from src.agent.market_data_intent import detect_market_data_intent

    assert detect_market_data_intent(
        "What is the current price right now?"
    ) is None


@pytest.mark.unit
def test_does_not_intercept_without_market_keyword() -> None:
    """Symbol alone is not enough — must also have a market-data verb."""
    from src.agent.market_data_intent import detect_market_data_intent

    assert detect_market_data_intent("BTC-USDT") is None
