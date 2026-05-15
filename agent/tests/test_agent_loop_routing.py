"""Integration test: AgentLoop must short-circuit via MarketDataDispatcher
for vague market-data prompts and never invoke the LLM.

This is the hard acceptance criterion from the Patch 3 briefing translated
into a pytest assertion: mock LLM, run vague prompt, assert .stream_chat
was never called.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest


def _build_loop(tmp_path: Path, market_data_response: str, llm_mock: MagicMock):
    from src.agent.loop import AgentLoop
    from src.agent.memory import WorkspaceMemory
    from src.agent.tools import ToolRegistry

    registry = ToolRegistry()

    # Fake get_market_data tool: returns the canned response.
    fake_tool = MagicMock()
    fake_tool.name = "get_market_data"
    fake_tool.repeatable = True
    fake_tool.is_readonly = True
    fake_tool.execute = MagicMock(return_value=market_data_response)
    registry.register(fake_tool)

    memory = WorkspaceMemory(run_dir=str(tmp_path))
    loop = AgentLoop(llm=llm_mock, registry=registry, memory=memory)
    return loop


@pytest.mark.unit
def test_loop_does_not_call_llm_for_vague_market_prompt(tmp_path: Path) -> None:
    llm = MagicMock()
    llm.stream_chat = MagicMock()
    llm.chat = MagicMock()

    response = json.dumps({
        "status": "ok", "symbol": "BTC/USDT", "provider": "ccxt",
        "timeframe": "1d", "current_price": 79250.0,
        "candles": [{"date": "2026-05-09", "open": 1, "high": 2, "low": 0.5,
                     "close": 1.5, "volume": 100}],
    })
    loop = _build_loop(tmp_path, response, llm)

    result = loop.run(
        "Obtenha o preço atual do BTC-USDT e os últimos 7 dias de fechamento "
        "diário. Mostre como uma tabela."
    )

    assert llm.stream_chat.call_count == 0, (
        f"LLM was invoked {llm.stream_chat.call_count} times — Patch 3 "
        "dispatcher should short-circuit before the ReAct loop runs."
    )
    assert llm.chat.call_count == 0
    assert result.get("iterations") == 0
    assert result.get("routed_by") == "market_data_router"
    assert result.get("status") in ("success", "ok")


@pytest.mark.unit
def test_loop_invokes_llm_for_backtest_prompt(tmp_path: Path) -> None:
    """Anti-regression: non-market prompts must still go through the LLM."""
    from src.providers.chat import LLMResponse

    llm = MagicMock()
    llm.stream_chat = MagicMock(return_value=LLMResponse(
        content="ok", tool_calls=[], finish_reason="stop"
    ))
    llm.chat = MagicMock(return_value=LLMResponse(
        content="ok", tool_calls=[], finish_reason="stop"
    ))

    loop = _build_loop(tmp_path, "{}", llm)

    result = loop.run("Backtest a BTC-USDT 20/50 moving-average strategy")

    assert llm.stream_chat.call_count >= 1, (
        "Non-market prompt was incorrectly short-circuited."
    )
    assert result.get("routed_by") != "market_data_router"
