# Demo Readiness Checklist

This checklist verifies that the Beginner Trail can be demonstrated safely.
It defines the permitted demo sequence, the expected output for each level,
and the hard limits on what must never be claimed or performed during a demo.

---

## Objective

Demonstrate that the four deterministic dispatchers (Levels 1–4) intercept
specific prompt classes, execute their workflows without LLM orchestration,
and return structured results — all within a local Docker environment using
historical or simulated data only.

**This is a research and engineering demo.** It does not involve real capital,
live orders, or investment advice of any kind.

---

## Prohibited Actions — Read Before Starting

The following are **strictly forbidden** during any demo session:

| Prohibited | Reason |
|---|---|
| Placing real orders on any exchange | System has no exchange integration |
| Placing paper trading orders | No paper trading engine is connected |
| Claiming future profitability from backtest results | Past performance does not predict future returns |
| Providing investment or financial advice | This is not a financial advisory system |
| Claiming that Swarm agent outputs are factually verified | Factual accuracy depends on the underlying model; content is not audited |
| Claiming that backtest results account for costs or slippage | The default MA-crossover backtest uses no transaction cost or slippage model |
| Presenting any output as a trading recommendation | All outputs are for research and simulation only |

Violation of any of the above is a demo failure, regardless of technical outcome.

---

## Prerequisites

Before starting the demo, verify all of the following:

- [ ] Docker is running (`docker ps` returns without error)
- [ ] Fork container is up (`docker compose ps` shows the agent container as `Up`)
- [ ] Environment variables loaded: `OPENROUTER_API_KEY` (or equivalent) is set in `.env`
- [ ] `docs/BEGINNER_TRAIL.md` is accessible and lists all 4 SEALED levels
- [ ] Unit suite passes locally:
  ```bash
  cd agent && python -m pytest tests/ -m unit -q
  ```
  Expected: all unit tests green (174+ passing)

If any prerequisite fails, do not proceed with the demo.

---

## Bringing Up the Environment

```bash
# From repo root
docker compose build      # only needed after code changes
docker compose up -d      # start containers in background
docker compose ps         # verify status = Up
```

To send a prompt manually (replace `<PROMPT>` with the demo prompt):

```bash
docker exec -it <container_name> python cli.py --message "<PROMPT>"
```

Container name can be found with `docker compose ps`.

---

## Demo Sequence

Run the four levels in order. Each level must pass before moving to the next.

---

### Level 1 — Market Data Routing

**Canonical prompt:**
```
Get the current price of ETH-USDT and last 30 days closing prices.
```

**Expected output (PASS criteria):**
- `routed_by: market_data_router`
- `iterations: 0`
- Table of OHLCV candles for ETH-USDT
- No `web_search` or `read_url` tool calls in trace
- No LLM turn in trace

**FAIL indicators:**
- `iterations > 0` (LLM was invoked)
- `routed_by` absent or different
- `web_search` or `read_url` appears in trace
- Error or exception in output

---

### Level 2 — Candlestick Workflow

**Canonical prompt:**
```
Analyze the candlestick patterns on BTC-USDT daily for the last 60 days.
```

**Expected output (PASS criteria):**
- `routed_by: candlestick_workflow`
- `iterations: 0`
- `verdict` in `{bullish, bearish, neutral, no_clear_signal}`
- Candle data fetched via `get_market_data`
- No LLM turn in trace

**FAIL indicators:**
- Missing or empty `verdict`
- `iterations > 0`
- `routed_by` absent or different

---

### Level 3 — Backtest Workflow

**Canonical prompt:**
```
Backtest a 20/50 MA crossover on BTC-USDT from 2024-01-01 to 2024-12-31 with 10000 USDT.
```

**Expected output (PASS criteria):**
- `routed_by: backtest_workflow`
- `iterations: 0`
- Numeric metrics present: Sharpe ratio, max drawdown, total return, trade count
- Metrics sourced from `artifacts/metrics.csv` (historical simulation)
- No LLM turn in trace

**FAIL indicators:**
- Non-numeric or missing metrics
- `iterations > 0`
- Fabricated metrics (no `metrics.csv` produced)

**Mandatory disclaimer to state during demo:**
> "These are backtested results on historical data from 2024. They do not include
> transaction costs or slippage, and they do not predict future performance."

---

### Level 4 — Swarm Workflow

**Canonical prompt:**
```
Run the crypto_research_lab swarm on ETH with timeframe 30d.
```

**Expected output (PASS criteria):**
- `routed_by: swarm_workflow`
- `iterations: 0`
- `run_swarm` was invoked directly (confirmed in trace as `tool_call(run_swarm)`)
- `final_report` non-empty
- At least 1 agent task with `status: completed`
- No LLM turn before `run_swarm` in trace

**FAIL indicators:**
- JSON-like tool call text in output (FAIL_MODEL pattern — `run_swarm` was never actually called)
- `iterations > 0`
- `final_report` empty or absent
- Zero completed agent tasks

**Mandatory disclaimer to state during demo:**
> "The Swarm validates that agents ran and produced a consolidated report.
> It does not verify the factual accuracy of on-chain data interpretations,
> DeFi metrics, or sentiment scores. Content quality depends on the model
> and available data feeds."

---

## Running the Canaries

After the demo sequence, run the canary suite to confirm no regressions:

```bash
cd agent

# Anti-drift canaries (doc contracts)
python -m pytest tests/test_beginner_trail_doc.py -v
python -m pytest tests/test_demo_readiness_doc.py -v

# SEALED baseline canaries (runtime contracts)
python -m pytest tests/test_baseline_market_data_routing.py -v
python -m pytest tests/test_baseline_candlestick_workflow.py -v
python -m pytest tests/test_baseline_backtest_workflow.py -v
python -m pytest tests/test_baseline_swarm_workflow.py -v

# Full unit suite
python -m pytest tests/ -m unit -q
```

All tests must pass. Any failure is a demo blocker.

---

## PASS / FAIL Criteria Summary

| Level | PASS requires | FAIL if |
|---|---|---|
| N1 Market Data | `routed_by=market_data_router`, `iterations=0`, OHLCV table | LLM invoked, web tool used, no table |
| N2 Candlestick | `routed_by=candlestick_workflow`, `iterations=0`, verdict present | No verdict, LLM invoked |
| N3 Backtest | `routed_by=backtest_workflow`, `iterations=0`, numeric metrics | Non-numeric metrics, LLM invoked, no metrics.csv |
| N4 Swarm | `routed_by=swarm_workflow`, `iterations=0`, `run_swarm` called, report non-empty, ≥1 task completed | JSON-like text output, LLM invoked, empty report, 0 tasks |
| Canaries | All unit tests green | Any test failure |

---

## Troubleshooting

| Symptom | Likely cause | Resolution |
|---|---|---|
| `routed_by` missing or wrong dispatcher | Old container image with stale code | `docker compose build && docker compose up -d` |
| `iterations > 0` for any level | Dispatcher not firing (intent not matched) | Check prompt matches canonical form exactly; check dispatcher import in `loop.py` |
| Level 4 output is JSON text, not a structured result | FAIL_MODEL pattern — model printed tool call as text | Confirm `SwarmWorkflowDispatcher` is imported and called before ReAct in `loop.py` |
| `final_report` empty (Level 4) | Swarm timeout or all agents failed | Increase `SWARM_TIMEOUT` env var; check agent logs in `agent/runs/` |
| Canary test fails | Baseline doc or runtime contract regressed | Check which class (A–E) failed; do not patch the canary — fix the root cause |

---

## What NOT to Demonstrate

Do not demonstrate or imply any of the following:

- **Live trading execution** — There is no exchange adapter or live order routing.
- **Paper trading** — No sandbox trading engine is connected.
- **Alpha signals as actionable recommendations** — Swarm outputs are research
  artifacts; present them as informational only.
- **Backtest metrics as forward-looking predictions** — Always pair backtest
  results with the cost/slippage caveat.
- **Swarm factual accuracy** — The dispatcher validates structure, not content.
  Do not claim that on-chain data, DeFi metrics, or sentiment scores are verified.
- **Financial advice of any kind** — This system is not registered as a financial
  advisor. Outputs must not be presented as investment guidance.

---

## Disclaimer

This demo operates on historical data and local simulation only.
No real capital is at risk. No orders are placed on any exchange.
All outputs — including backtest metrics and Swarm agent reports — are for
research and engineering evaluation only. They do not constitute investment advice
and must not be used to make financial decisions without independent verification.

See [BEGINNER_TRAIL.md](BEGINNER_TRAIL.md) and the [main README Disclaimer](../README.md#disclaimer).
