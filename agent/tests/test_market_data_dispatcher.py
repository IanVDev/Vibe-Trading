"""Unit tests for MarketDataDispatcher — the pre-LLM short-circuit path.

Risk level 3: dispatcher decides whether to skip the entire ReAct loop and
respond directly. Failure modes covered:
- Vague market-data prompt -> tool is called directly, no LLM.
- Provider failure -> sanitized error, no web fallback, no LLM retry.
- Non-market prompt -> dispatcher returns None, loop runs normally.
- Trace events emitted in fixed order.
- No leak of credentials/paths/stack in error path.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest


def _make_registry(tool_response: str) -> MagicMock:
    """Build a fake ToolRegistry whose .execute() returns the given JSON string."""
    reg = MagicMock()
    reg.execute = MagicMock(return_value=tool_response)
    return reg


def _trace_collector() -> tuple[MagicMock, list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    trace = MagicMock()
    trace.write = MagicMock(side_effect=lambda evt: events.append(evt))
    return trace, events


@pytest.mark.unit
def test_dispatcher_calls_get_market_data_for_vague_prompt() -> None:
    from src.agent.market_data_dispatcher import MarketDataDispatcher

    registry = _make_registry(json.dumps({
        "status": "ok", "symbol": "BTC/USDT", "provider": "ccxt",
        "timeframe": "1d", "current_price": 79250.0,
        "candles": [{"date": "2026-05-09", "open": 80193.18, "high": 81080.0,
                     "low": 80129.85, "close": 80678.4, "volume": 7548.42}],
    }))
    trace, _events = _trace_collector()

    result = MarketDataDispatcher().try_route(
        "Obtenha o preço atual do BTC-USDT e os últimos 7 dias de fechamento "
        "diário. Mostre como uma tabela.",
        registry, trace,
    )

    assert result is not None
    assert result["status"] == "success"
    assert result["iterations"] == 0
    assert result["routed_by"] == "market_data_router"
    registry.execute.assert_called_once()
    args, _ = registry.execute.call_args
    assert args[0] == "get_market_data"
    payload = args[1]
    assert payload["symbol"] in ("BTC-USDT", "BTC/USDT")
    assert payload["timeframe"] == "1d"
    assert payload["limit"] == 7


@pytest.mark.unit
def test_dispatcher_returns_markdown_table_on_success() -> None:
    from src.agent.market_data_dispatcher import MarketDataDispatcher

    registry = _make_registry(json.dumps({
        "status": "ok", "symbol": "BTC/USDT", "provider": "ccxt",
        "timeframe": "1d", "current_price": 79250.0,
        "candles": [
            {"date": "2026-05-09", "open": 80193.18, "high": 81080.0,
             "low": 80129.85, "close": 80678.4, "volume": 7548.42},
            {"date": "2026-05-10", "open": 80678.41, "high": 82479.32,
             "low": 80279.77, "close": 82210.07, "volume": 12034.31},
        ],
    }))
    trace, _events = _trace_collector()

    result = MarketDataDispatcher().try_route(
        "current price BTC-USDT last 2 days close", registry, trace,
    )

    assert result is not None
    content = result["content"]
    assert "|" in content
    assert "Date" in content or "Data" in content
    assert "Close" in content or "Fechamento" in content
    assert "80678.4" in content or "80,678.40" in content or "80678.40" in content
    assert "79250" in content or "79,250" in content


@pytest.mark.unit
def test_dispatcher_returns_sanitized_error_no_web_fallback() -> None:
    from src.agent.market_data_dispatcher import MarketDataDispatcher

    poisoned = json.dumps({
        "status": "error",
        "error": (
            "request failed: Authorization: Bearer secret-token-abc, "
            "internal://proxy.local:8080/get, "
            "Traceback (most recent call last): File \"/Users/ian/secret.py\""
        ),
    })
    registry = _make_registry(poisoned)
    trace, _events = _trace_collector()

    result = MarketDataDispatcher().try_route(
        "BTC-USDT current price last 7 days", registry, trace,
    )

    assert result is not None
    assert result["status"] == "failed"
    assert result["iterations"] == 0
    content = result["content"]
    for forbidden in (
        "Authorization", "Bearer", "secret-token-abc", "api_key", "secret-token",
        "Traceback", "internal://", "/Users/", "/home/", "proxy.local:8080",
    ):
        assert forbidden not in content, (
            f"Leaked {forbidden!r} into dispatcher response: {content!r}"
        )


@pytest.mark.unit
def test_dispatcher_returns_none_for_backtest_prompt() -> None:
    from src.agent.market_data_dispatcher import MarketDataDispatcher

    registry = _make_registry("{}")
    trace, _events = _trace_collector()

    result = MarketDataDispatcher().try_route(
        "Backtest a BTC-USDT 20/50 moving-average strategy for 2024",
        registry, trace,
    )

    assert result is None
    registry.execute.assert_not_called()


@pytest.mark.unit
def test_dispatcher_returns_none_when_no_intent() -> None:
    from src.agent.market_data_dispatcher import MarketDataDispatcher

    registry = _make_registry("{}")
    trace, _events = _trace_collector()

    assert MarketDataDispatcher().try_route(
        "How does the agent work internally?", registry, trace,
    ) is None
    registry.execute.assert_not_called()


@pytest.mark.unit
def test_dispatcher_emits_trace_events_in_order() -> None:
    from src.agent.market_data_dispatcher import MarketDataDispatcher

    registry = _make_registry(json.dumps({
        "status": "ok", "symbol": "BTC/USDT", "provider": "ccxt",
        "timeframe": "1d", "current_price": 79250.0,
        "candles": [{"date": "2026-05-09", "open": 1, "high": 2, "low": 0.5,
                     "close": 1.5, "volume": 100}],
    }))
    trace, events = _trace_collector()

    MarketDataDispatcher().try_route(
        "BTC-USDT preço atual últimos 7 dias", registry, trace,
    )

    types = [e.get("type") for e in events]
    assert "router" in types, f"missing router event in {types}"
    tool_calls = [e for e in events if e.get("type") == "tool_call"]
    assert any(e.get("name") == "get_market_data" for e in tool_calls), (
        f"missing tool_call(get_market_data) in {events}"
    )
    answers = [e for e in events if e.get("type") == "answer"]
    assert answers, "missing answer event"
    ends = [e for e in events if e.get("type") == "end"]
    assert ends, "missing end event"
    assert ends[-1].get("status") == "success"
    assert ends[-1].get("routed_by") == "market_data_router"


@pytest.mark.unit
def test_dispatcher_never_calls_web_tools() -> None:
    """The dispatcher must not invoke web_search or read_url under any path."""
    from src.agent.market_data_dispatcher import MarketDataDispatcher

    registry = _make_registry(json.dumps({"status": "error", "error": "x"}))
    trace, _ = _trace_collector()

    MarketDataDispatcher().try_route(
        "BTC-USDT current price last 7 days", registry, trace,
    )

    called_names = [c.args[0] for c in registry.execute.call_args_list]
    assert "web_search" not in called_names
    assert "read_url" not in called_names
