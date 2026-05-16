# Project State — v0.1

**Version:** 0.1  
**Date:** 2026-05-16  
**Classification:** Research / Simulation Only — Not a financial product  
**Repo:** [IanVDev/Vibe-Trading](https://github.com/IanVDev/Vibe-Trading)

This document is a point-in-time snapshot of what has been built, verified,
and documented. It does not imply production readiness, financial utility,
or factual accuracy of agent outputs.

---

## Component Status

| Component | SEALED | Runtime | Documented | Enabled |
|---|---|---|---|---|
| N1 — Market Data Routing | Yes (PR #4) | PASS | BEGINNER_TRAIL | — |
| N2 — Candlestick Workflow | Yes (PR #6) | PASS | BEGINNER_TRAIL | — |
| N3 — Backtest Workflow | Yes (PR #8) | PASS (real Docker) | BEGINNER_TRAIL | — |
| N4 — Swarm Workflow | Yes (PR #10) | PASS (real Docker) | BEGINNER_TRAIL | — |
| Swarm Evidence Quality Gate | — | PASS (smoke, PR #15) | SWARM_WORKFLOW_BASELINE §15 | Yes |
| Beginner Trail | — | — | BEGINNER_TRAIL.md | — |
| Demo Readiness Checklist | — | — | DEMO_READINESS_CHECKLIST.md | — |
| Local Gate Runbook | — | — | LOCAL_GATE_RUNBOOK.md | — |
| Release Demo Packet v0.1 | — | — | RELEASE_DEMO_PACKET_V0_1.md | — |

---

## Patch History (P1–P15)

| Patches | Layer | What was delivered |
|---|---|---|
| P1–P2 | Tools | `get_market_data` first-class tool + skill-name guards |
| P3–P4 | N1 SEALED | Deterministic market data dispatcher + baseline canary |
| P5–P6 | N2 SEALED | Candlestick workflow dispatcher + baseline canary |
| P7–P8 | N3 SEALED | MA-crossover backtest dispatcher + baseline canary |
| P9–P10 | N4 SEALED | SwarmWorkflowDispatcher (pre-LLM) + baseline canary |
| P11 | Docs | Beginner Trail — 4 SEALED levels documented |
| P12 | Docs | Demo Readiness Checklist |
| P13 | Docs | Local Gate Runbook (CI substitute) |
| P14 | Docs | Release Demo Packet v0.1 |
| P15 | Feature | SwarmEvidenceQualityGate — minimum evidence layer |

---

## Evidence Quality Gate — Smoke Result (Patch 15)

**Run date:** 2026-05-16  
**Prompt:** `Run the crypto_research_lab swarm on ETH with timeframe 30d.`  
**Run ID:** `swarm-20260516-025543-207dda18`

**Trace:**
```
start         → prompt received
router        → swarm_workflow (intent: preset=crypto_research_lab, target=ETH, timeframe=30d)
tool_call     → run_swarm
tool_result   → run_swarm  (~225 s)
workflow_step → validate_report (task_count=4, completed=4)
quality_gate  → evidence_quality_gate
                gate_status=pass
                has_evidence=true
                has_limitations_section=true
                warnings=[]
answer
end           → status=success, iterations=0, routed_by=swarm_workflow
```

**Agents executed (4/4 completed):**

| Agent | Status | Summary excerpt |
|---|---|---|
| onchain_analyst | completed | On-Chain Analysis Report: BTC, ETH, SOL |
| defi_analyst | completed | DeFi Ecosystem Health — TVL at highest point |
| crypto_sentiment_analyst | completed | Sentiment analysis across assets |
| alpha_synthesizer | completed | Three-Dimensional Signal Summary Table |

**Report:** 1,019 characters — contains evidence keywords (bullish, bearish, neutral, tvl, on-chain) and limitation keyword ("risk"). Final report produced.  
**Gate status:** pass — no warnings.  
**No LLM fallback. No web tools. No success without run_swarm invocation.**

---

## Test Evidence

| Test suite | Count | Result |
|---|---|---|
| SEALED N1 canary | 21 | passed |
| SEALED N2 canary | 21 | passed |
| SEALED N3 canary | 18 | passed |
| SEALED N4 canary | 24 | passed |
| Evidence gate unit | 9 | passed |
| Docs anti-drift (all) | 27+ | passed |
| **Total** | **93+** | **all green** |

Gates run locally. No remote CI. See `LOCAL_GATE_RUNBOOK.md`.

---

## Real Limitations

The following limitations are real and must not be minimised when presenting
or discussing this project:

- **No live trading.** The system does not place orders on any exchange.
  There is no exchange adapter. No capital is at risk.
- **No paper trading.** No sandbox trading engine is connected.
- **Backtest is historical simulation only.** The MA-crossover backtest
  (Level 3) runs on historical OHLCV data. It does not account for
  transaction costs, spread, slippage, or market impact. Results describe
  what would have occurred under these parameters in the tested window.
  They do not predict future performance.
- **Evidence gate is structural, not semantic.** `SwarmEvidenceQualityGate`
  checks for the presence of analytical keywords in the report corpus. A
  report that contains one matching keyword but no meaningful analysis will
  still pass the gate. The gate is a minimum bar — it is not a quality
  audit and it does not verify factual accuracy.
- **Swarm factual accuracy is not audited.** On-chain data interpretations,
  DeFi TVL figures, and sentiment scores produced by swarm agents are not
  independently verified. Content quality depends on the underlying model
  and available data feeds.
- **No walk-forward or out-of-sample validation.** Backtest results are
  in-sample only. No robustness testing has been performed.
- **Preset allowlist is fixed at 25 presets.** Custom swarm prompts without
  an explicit preset name fall through to the LLM/ReAct loop.
- **No remote CI.** Gates are run locally. See `LOCAL_GATE_RUNBOOK.md` for
  the gate policy and evidence format.

---

## Residual Risks

| Risk | Notes |
|---|---|
| Keyword matching (gate) | A trivially-written report with one evidence keyword passes the gate. Future work: semantic validation or agent-level evidence fields. |
| Model quality variance | Swarm outputs depend on the configured model. Weaker models may fail to produce evidence-rich reports, triggering gate=partial. |
| Stale container | If container has old code, gate is not active. Always update via `docker cp` or rebuild before demo. |
| Gate bypass via partial | A `status=partial` result is not a hard failure. The loop.py caller decides how to handle partial — this is not yet tested end-to-end. |
| In-sample backtest | MA-crossover results for 2024 BTC-USDT are specific to that period. No out-of-sample guarantee. |

---

## Prohibited Claims

The following must never be stated or implied:

| Prohibited | Reason |
|---|---|
| "This is a trading system." | No orders are placed. |
| "This predicts market movements." | Backtest results are historical and in-sample. |
| "The swarm is factually accurate." | Content is not audited. |
| "The evidence gate verifies facts." | It checks keywords, not factual correctness. |
| "This will generate profit." | No performance guarantee exists. |
| "You can use this for investment decisions." | This is not investment advice. |
| "This is ready for production use." | It is a research and simulation environment only. |

---

## Next Recommended Steps

These are engineering improvements that would meaningfully raise the quality
bar. None are committed or scheduled.

| Area | Description |
|---|---|
| **Semantic evidence validation** | Replace keyword matching in `SwarmEvidenceQualityGate` with a structured evidence schema: each agent must return a verifiable data point (price, TVL figure, on-chain metric) rather than a keyword. |
| **Backtest cost model** | Add configurable transaction cost and slippage parameters to the Level 3 dispatcher. |
| **Walk-forward validation** | Re-run backtest on a held-out period; flag strategies that only work in-sample. |
| **Remote CI** | GitHub Actions or self-hosted runner for the SEALED canary suite. Currently blocked by operational cost. |
| **partial status handling in loop.py** | Define and test what loop.py does when a dispatcher returns `status=partial`. Currently unspecified. |
| **Agent evidence schema** | Require each swarm agent to return structured evidence fields (source, value, timestamp) alongside narrative summaries. |

---

## Disclaimer

This project is a research and simulation environment. It is not a trading
system, not a financial advisor, and not a production service. No orders are
placed on any exchange. All backtest results are historical simulations and
do not predict future performance. Swarm agent outputs are not independently
verified for factual accuracy.

See [BEGINNER_TRAIL.md](BEGINNER_TRAIL.md), [DEMO_READINESS_CHECKLIST.md](DEMO_READINESS_CHECKLIST.md),
and the [main README Disclaimer](../README.md#disclaimer).
