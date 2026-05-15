# Beginner Trail Status

This document tracks the deterministic pre-LLM dispatcher stack built on top of
[IanVDev/Vibe-Trading](https://github.com/IanVDev/Vibe-Trading). Each level adds
a short-circuit in `AgentLoop.run()` that handles a specific class of prompts
without relying on the LLM to orchestrate tool calls.

---

## Trail Overview

| Level | Name | Status | Baseline Doc | Canary |
|-------|------|--------|--------------|--------|
| 1 | Market Data Routing | **SEALED** (PR #4) | [MARKET_DATA_ROUTING_BASELINE.md](MARKET_DATA_ROUTING_BASELINE.md) | `test_baseline_market_data_routing.py` |
| 2 | Candlestick Workflow | **SEALED** (PR #6) | [CANDLESTICK_WORKFLOW_BASELINE.md](CANDLESTICK_WORKFLOW_BASELINE.md) | `test_baseline_candlestick_workflow.py` |
| 3 | Backtest Workflow | **SEALED** (PR #8) | [BACKTEST_WORKFLOW_BASELINE.md](BACKTEST_WORKFLOW_BASELINE.md) | `test_baseline_backtest_workflow.py` |
| 4 | Swarm Workflow | **SEALED** (PR #10) | [SWARM_WORKFLOW_BASELINE.md](SWARM_WORKFLOW_BASELINE.md) | `test_baseline_swarm_workflow.py` |

Dispatcher execution order in `loop.py`:
```
market_data → candlestick → backtest → swarm → ReAct/LLM fallback
```

---

## Level Detail

### Level 1 — Market Data Routing

**Objective:** Return current price and recent OHLCV data for simple price queries
without invoking the LLM.

| Field | Value |
|-------|-------|
| Dispatcher | `MarketDataDispatcher` |
| Module | `agent/src/agent/market_data_dispatcher.py` |
| Intent detector | `agent/src/agent/market_data_intent.py` |
| Canonical prompt | `"Get the current price of ETH-USDT and last 30 days closing prices."` |
| Success contract | `status=success`, `routed_by=market_data_router`, `iterations=0`, table of candles |
| Principal fail-closed | Tool returns error → sanitised failure, never web_search/LLM fallback |

---

### Level 2 — Candlestick Workflow

**Objective:** Run a candlestick pattern analysis (bullish / bearish / neutral /
no_clear_signal) for simple pattern recognition prompts without invoking the LLM
to orchestrate the tool sequence.

| Field | Value |
|-------|-------|
| Dispatcher | `CandlestickWorkflowDispatcher` |
| Module | `agent/src/agent/candlestick_workflow.py` |
| Intent detector | `agent/src/agent/candlestick_intent.py` |
| Canonical prompt | `"Analyze the candlestick patterns on BTC-USDT daily for the last 60 days."` |
| Success contract | `status=success`, `routed_by=candlestick_workflow`, `iterations=0`, verdict in {bullish,bearish,neutral,no_clear_signal} |
| Principal fail-closed | `get_market_data` error → skips pattern tool, returns failure; never web_search/LLM |

---

### Level 3 — Backtest Workflow

**Objective:** Execute a simple MA-crossover backtest end-to-end (write config →
write signal engine → run backtest → read metrics) and return Sharpe ratio, max
drawdown, total return, and trade count — without the LLM orchestrating the steps.

| Field | Value |
|-------|-------|
| Dispatcher | `BacktestWorkflowDispatcher` |
| Module | `agent/src/agent/backtest_workflow.py` |
| Intent detector | `agent/src/agent/backtest_intent.py` |
| Signal template | `_MA_CROSSOVER_TEMPLATE` (string constant, never LLM-generated) |
| Canonical prompt | `"Backtest a 20/50 MA crossover on BTC-USDT from 2024-01-01 to 2024-12-31 with 10000 USDT."` |
| Success contract | `status=success`, `routed_by=backtest_workflow`, `iterations=0`, numeric metrics from `artifacts/metrics.csv` |
| Principal fail-closed | Missing or non-numeric metrics → fail; fabricated metrics are a regression |

---

### Level 4 — Swarm Workflow

**Objective:** Execute a named-preset multi-agent swarm (e.g. `crypto_research_lab`)
by invoking `run_swarm` directly from Python — bypassing the LLM that was observed
to print tool call syntax as plain text without executing it (FAIL_MODEL pattern).

| Field | Value |
|-------|-------|
| Dispatcher | `SwarmWorkflowDispatcher` |
| Module | `agent/src/agent/swarm_workflow.py` |
| Intent detector | `agent/src/agent/swarm_intent.py` |
| Preset allowlist | 25 presets from `SwarmTool._PRESET_KEYWORDS` |
| Canonical prompt | `"Run the crypto_research_lab swarm on ETH with timeframe 30d."` |
| Success contract | `status=success`, `routed_by=swarm_workflow`, `iterations=0`, `run_swarm` invoked, `final_report` non-empty, at least 1 task `status=completed` |
| Principal fail-closed | Empty `final_report`, zero completed tasks, or `status≠completed` → fail; JSON-like text output is a regression |

---

## What Is NOT Guaranteed

The trail establishes deterministic routing, execution, and structural validation
for specific prompt classes. The following remain outside its scope:

- **Real or live trading** — The system does not execute orders on any exchange.
  All backtests are simulations on historical data.
- **Paper trading / sandbox execution** — No paper trading integration is included
  in this trail.
- **Future profitability** — Backtested results do not predict future returns.
  Past performance is not a guarantee of future results.
- **Statistical robustness** — The MA-crossover backtest does not include
  transaction costs, slippage, walk-forward validation, or out-of-sample testing
  by default.
- **Factual correctness of agent outputs (Swarm)** — The Level 4 dispatcher
  validates that `run_swarm` was invoked, that agents reported status, and that a
  consolidated report was produced. It does not verify the factual accuracy of
  on-chain data interpretations, DeFi metrics, or sentiment scores generated by
  the agents. Content quality depends on the underlying model and available data.
- **Financial advice** — Nothing in this system constitutes investment advice.

---

## Next Possible Steps

These are natural extensions of the trail but are not yet implemented:

| Area | Description |
|------|-------------|
| **Evidence Quality Gate** | Validate that Swarm agent outputs contain specific evidence markers (source citations, numeric values from verified data feeds) before accepting a report as complete. |
| **Backtest cost/slippage** | Extend the MA-crossover workflow to include configurable transaction cost and slippage parameters. |
| **Walk-forward validation** | Add an out-of-sample validation step that re-runs the backtest on a held-out period and flags overfitted strategies. |
| **Paper trading sandbox** | Connect the backtest dispatcher output to a paper trading engine that simulates live execution without real capital. |
| **CI on fork** | Set up GitHub Actions on `IanVDev/Vibe-Trading` to run the four SEALED canaries on every PR. |
| **Release demo checklist** | A structured checklist verifying all four levels pass a smoke test before a release tag is created. |

---

## Disclaimer

This project is for research, simulation, and backtesting only. It is not
investment advice and it does not execute live trades. See the [main README
Disclaimer](../README.md#disclaimer) for full terms.

The deterministic dispatchers in this trail are engineering guardrails, not
financial guarantees. Any outputs — including backtest metrics and agent
reports — should be independently verified before being used to inform financial
decisions.
