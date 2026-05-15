# Release Demo Packet — v0.1

**Version:** 0.1  
**Date:** 2026-05-15  
**Status:** Research / Simulation Only — Not a financial product  
**Repo:** [IanVDev/Vibe-Trading](https://github.com/IanVDev/Vibe-Trading)

---

## Objective

This packet guides a safe, accurate demonstration of the Vibe Trading dispatcher
stack. It defines what to show, what to say, and — critically — what must never
be claimed.

---

## Product Vision

Vibe Trading is a **research and backtesting environment** built on a stack of
deterministic pre-LLM dispatchers. Each dispatcher intercepts a specific class of
prompt and executes a structured workflow — without relying on the LLM to
orchestrate tool calls. The result is reproducible, auditable behaviour for four
categories of financial research prompts.

This is **not** a trading system. It does not place orders. It does not manage
capital. It does not provide investment advice. All outputs are for research and
engineering evaluation only.

---

## Current State — 4 SEALED Levels

| Level | Name | SEALED | Runtime | Canary |
|---|---|---|---|---|
| 1 | Market Data Routing | Yes (PR #4) | OK | `test_baseline_market_data_routing.py` |
| 2 | Candlestick Workflow | Yes (PR #6) | OK | `test_baseline_candlestick_workflow.py` |
| 3 | Backtest Workflow | Yes (PR #8) | PASS — real Docker | `test_baseline_backtest_workflow.py` |
| 4 | Swarm Workflow | Yes (PR #10) | PASS — real Docker | `test_baseline_swarm_workflow.py` |

Full trail documentation: [BEGINNER_TRAIL.md](BEGINNER_TRAIL.md)

---

## Supporting Documentation

| Document | Purpose |
|---|---|
| [BEGINNER_TRAIL.md](BEGINNER_TRAIL.md) | Trail overview, dispatcher detail, success contracts |
| [DEMO_READINESS_CHECKLIST.md](DEMO_READINESS_CHECKLIST.md) | Step-by-step demo sequence, PASS/FAIL criteria, troubleshooting |
| [LOCAL_GATE_RUNBOOK.md](LOCAL_GATE_RUNBOOK.md) | Gate commands, PR-FLOW evidence format, NÃO EXECUTADO rule |

Before proceeding, verify all three documents are accessible and current.

---

## Recommended Demo Sequence

Run the four levels in order. Present each as an independent capability, not as
steps toward a trading decision.

---

### Level 1 — Market Data Routing

**What it shows:** A simple price query is intercepted before reaching the LLM
and answered directly by fetching market data.

**Canonical prompt:**
```
Get the current price of ETH-USDT and last 30 days closing prices.
```

**Expected output:**
- `routed_by: market_data_router`
- `iterations: 0`
- Table of OHLCV candles for ETH-USDT
- No LLM turn in trace

**What to say:** "This query never reaches the LLM. The dispatcher recognises the
intent, fetches the data, and returns it directly."

---

### Level 2 — Candlestick Workflow

**What it shows:** A pattern recognition prompt is handled by a deterministic
workflow that fetches candles and applies a pattern analysis tool.

**Canonical prompt:**
```
Analyze the candlestick patterns on BTC-USDT daily for the last 60 days.
```

**Expected output:**
- `routed_by: candlestick_workflow`
- `iterations: 0`
- `verdict` in `{bullish, bearish, neutral, no_clear_signal}`

**What to say:** "The workflow fetches the candle data and runs pattern analysis.
The verdict is a structural classification — it is not a trading signal."

---

### Level 3 — Backtest Workflow

**What it shows:** A backtest request triggers a fully deterministic workflow:
write config → write signal engine → run backtest → read metrics. No LLM
involvement.

**Canonical prompt:**
```
Backtest a 20/50 MA crossover on BTC-USDT from 2024-01-01 to 2024-12-31 with 10000 USDT.
```

**Expected output:**
- `routed_by: backtest_workflow`
- `iterations: 0`
- Numeric metrics: Sharpe ratio, max drawdown, total return, trade count
- Metrics sourced from `artifacts/metrics.csv`

**What to say:** "This is a historical simulation on 2024 data. It does not
include transaction costs or slippage. The results describe what would have
happened under these parameters in this specific historical window — they do not
predict future performance."

---

### Level 4 — Swarm Workflow

**What it shows:** A named-preset multi-agent swarm is invoked deterministically.
`run_swarm` is called directly from Python, bypassing the LLM that was observed
to print tool call syntax as plain text without executing it.

**Canonical prompt:**
```
Run the crypto_research_lab swarm on ETH with timeframe 30d.
```

**Expected output:**
- `routed_by: swarm_workflow`
- `iterations: 0`
- `run_swarm` called (visible in trace as `tool_call(run_swarm)`)
- `final_report` non-empty
- At least 1 agent task with `status: completed`

**What to say:** "Four agents run in parallel and produce a consolidated research
report. The dispatcher validates that agents completed and a report was produced —
it does not audit the factual accuracy of on-chain data, DeFi metrics, or
sentiment scores. Content quality depends on the model and available data."

---

## Minimum Evidence Before Demo

Run the following gates from `LOCAL_GATE_RUNBOOK.md` before starting:

```bash
# From repo root — SEALED canaries (84 tests must pass)
.venv-test/bin/pytest \
  agent/tests/test_baseline_market_data_routing.py \
  agent/tests/test_baseline_candlestick_workflow.py \
  agent/tests/test_baseline_backtest_workflow.py \
  agent/tests/test_baseline_swarm_workflow.py -q

# Docs anti-drift (all must pass)
.venv-test/bin/pytest \
  agent/tests/test_beginner_trail_doc.py \
  agent/tests/test_demo_readiness_doc.py \
  agent/tests/test_local_gate_runbook_doc.py \
  agent/tests/test_release_demo_packet_doc.py -q
```

If any test fails, do not proceed with the demo.

---

## What NOT to Say

These statements are **prohibited** during any demo, Q&A, or follow-up:

| Prohibited statement | Why |
|---|---|
| "This is a trading system." | It is not. No orders are placed. |
| "You can use this to trade." | No live trading integration exists. |
| "The backtest shows this strategy is profitable." | Past simulation does not predict future returns. |
| "This is investment advice." | It is not. Not registered as a financial advisor. |
| "The Swarm agents are factually accurate." | Factual accuracy is not audited. Content depends on model and data. |
| "This executes orders on [exchange]." | No exchange adapter exists. |
| "You can paper trade with this." | No paper trading engine is connected. |
| "This will make money." | No performance guarantee exists or is implied. |

If asked any of these questions, redirect: "This is a research and simulation
environment. It does not place orders and does not provide financial advice."

---

## Known Limitations

- **No transaction costs or slippage in backtest.** The MA-crossover backtest
  uses a simple model with no commission, spread, or market impact.
- **No walk-forward validation.** Results are in-sample only.
- **No paper trading.** No sandbox trading engine is connected.
- **No live trading.** No exchange adapter exists.
- **Swarm factual accuracy not audited.** Agent outputs depend on the underlying
  model and available data feeds. On-chain metrics, DeFi TVL, and sentiment
  scores are not independently verified.
- **Preset allowlist is fixed.** Only 25 named swarm presets are supported.
  Custom swarm prompts without an explicit preset name fall through to the LLM.
- **Local model quality varies.** Results depend on the model configured in
  `.env`. Weaker models may exhibit FAIL_MODEL patterns (tool call JSON as text).

---

## Residual Risks

| Risk | Mitigation |
|---|---|
| Audience interprets backtest as forward-looking | Always pair Level 3 results with the cost/slippage and historical-only caveat |
| Swarm report cited as factual research | Preface with: "This is an agent-generated summary, not audited research" |
| Demo environment uses stale code | Run SEALED canaries before demo; rebuild Docker if any dispatcher changed |
| Presenter forgets prohibition list | Keep this document open during the demo |

---

## Pre-Demo Checklist

Before starting the demo, verify all items:

- [ ] Docker is running (`docker ps` returns without error)
- [ ] Agent container is up (`docker compose ps` shows `Up`)
- [ ] SEALED canaries pass: 84/84 green
- [ ] Docs anti-drift tests pass
- [ ] `.env` has valid API key(s)
- [ ] This document is open and prohibition list is visible
- [ ] Audience has been told: "Research and simulation only — not financial advice"

If any item is unchecked, do not start the demo.

---

## Post-Demo Checklist

After completing the demo:

- [ ] Confirm no prohibited statements were made (review "What NOT to Say")
- [ ] If questions were asked about trading/profit, confirm redirect was given
- [ ] Log any FAIL indicators observed during the demo for follow-up

---

## Disclaimer

All outputs produced during this demo — including price data, candlestick verdicts,
backtest metrics, and Swarm agent reports — are for research and engineering
evaluation only. They do not constitute investment advice. No orders were placed.
No real capital was at risk.

Backtest results describe a historical simulation under specific parameters. They
do not predict future performance, do not account for transaction costs or
slippage, and must not be used to make financial decisions without independent
verification.

See [BEGINNER_TRAIL.md](BEGINNER_TRAIL.md) and the [main README Disclaimer](../README.md#disclaimer).
