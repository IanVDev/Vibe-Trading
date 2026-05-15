# Local Gate Runbook

This runbook defines the mandatory local validation process for all PRs in this
repository. It replaces remote CI (GitHub Actions) for the time being.

---

## Objective

Ensure that every PR that merges into `main` has been validated locally with the
same rigour that a CI pipeline would enforce — without the operational cost of
maintaining remote CI infrastructure.

---

## Why GitHub Actions Are Disabled

GitHub Actions are **not configured in this repository at this time**.

Reason: operational cost. Running agent-level smokes on GitHub-hosted runners
(API keys, Docker images, swarm timeouts of 30+ minutes) is expensive and slow.

Substitute: **mandatory local gates + explicit evidence in every PR-FLOW report**.
The absence of remote CI does not reduce the bar — it shifts accountability to the
contributor, who must declare gates run and results obtained before requesting merge.

---

## Policy

1. **Every PR must declare its gates** in the PR-FLOW evidence block or commit
   message before merge.
2. **Gates not run must be declared `NÃO EXECUTADO` with a reason.** Omitting a
   gate is not the same as passing it — undeclared gates are treated as failures.
3. **Fingir execução é proibido.** Never mark a gate as passed without running it.
   If a gate was skipped intentionally, say so and explain why.
4. **Runtime smokes are opt-in** for doc-only PRs (Nível 2), but mandatory for any
   PR that modifies dispatchers, workflows, intent detectors, or loop integration.

---

## Gate Map by PR Type

| PR type | Mandatory gates | Runtime smoke |
|---|---|---|
| Doc-only / copy (Nível 1-2) | Docs anti-drift canaries | NÃO EXECUTADO (ok) |
| Dispatcher / workflow change (Nível 3) | Unit suite + SEALED canaries N1–N4 + affected docs | Recomendado |
| SEALED baseline change (Nível 4) | Unit suite + SEALED canaries N1–N4 + full docs | Obrigatório |
| Runtime / model change (Nível 4) | Unit suite + SEALED canaries N1–N4 + Docker smoke | Obrigatório |

---

## Commands

All commands are run from the `agent/` directory unless noted otherwise.
Use the project's test venv: `.venv-test/bin/pytest` (from repo root).

### SEALED canaries — N1 through N4

```bash
# From repo root
.venv-test/bin/pytest agent/tests/test_baseline_market_data_routing.py  -v   # N1
.venv-test/bin/pytest agent/tests/test_baseline_candlestick_workflow.py  -v   # N2
.venv-test/bin/pytest agent/tests/test_baseline_backtest_workflow.py     -v   # N3
.venv-test/bin/pytest agent/tests/test_baseline_swarm_workflow.py        -v   # N4

# All four at once
.venv-test/bin/pytest \
  agent/tests/test_baseline_market_data_routing.py \
  agent/tests/test_baseline_candlestick_workflow.py \
  agent/tests/test_baseline_backtest_workflow.py \
  agent/tests/test_baseline_swarm_workflow.py \
  -q
```

Expected: **84 passed**.

### Docs anti-drift canaries

```bash
.venv-test/bin/pytest agent/tests/test_beginner_trail_doc.py     -v
.venv-test/bin/pytest agent/tests/test_demo_readiness_doc.py     -v
.venv-test/bin/pytest agent/tests/test_local_gate_runbook_doc.py -v
```

### Unit suite (excluding deps not in .venv-test)

```bash
.venv-test/bin/pytest agent/tests/ -m unit -q \
  --ignore=agent/tests/test_security_auth_api.py \
  --ignore=agent/tests/test_settings_api.py \
  --ignore=agent/tests/test_upload_api.py \
  --ignore=agent/tests/test_upload_security.py \
  --ignore=agent/tests/test_swarm_grounding.py \
  --ignore=agent/tests/test_swarm_preset_inspect.py \
  --ignore=agent/tests/test_swarm_presets_packaging.py \
  --ignore=agent/tests/test_swarm_token_tracking.py \
  --ignore=agent/tests/test_swarm_worker_report.py \
  --ignore=agent/tests/test_swarm_run_metadata.py
```

The ignored files require `fastapi` or `yaml` which are not installed in
`.venv-test`. These are pre-existing and not related to the dispatcher stack.

### Runtime smoke — Docker (manual, Level 3-4)

Run when a dispatcher or workflow changes. Requires Docker and live API keys.

```bash
# Start or rebuild containers
docker compose build && docker compose up -d

# Level 1 — market data
docker exec <container> python cli.py --message \
  "Get the current price of ETH-USDT and last 30 days closing prices."

# Level 2 — candlestick
docker exec <container> python cli.py --message \
  "Analyze the candlestick patterns on BTC-USDT daily for the last 60 days."

# Level 3 — backtest (runtime smoke, may take 1–3 min)
docker exec <container> python cli.py --message \
  "Backtest a 20/50 MA crossover on BTC-USDT from 2024-01-01 to 2024-12-31 with 10000 USDT."

# Level 4 — swarm (runtime smoke, may take 10–30 min)
docker exec -e SWARM_TIMEOUT=1800 <container> python cli.py --message \
  "Run the crypto_research_lab swarm on ETH with timeframe 30d."
```

PASS criteria for each level: see `docs/DEMO_READINESS_CHECKLIST.md`.

---

## When to Run the Manual Smoke

| Condition | Smoke required |
|---|---|
| PR modifies `loop.py` | Yes — all 4 levels |
| PR modifies a dispatcher (`*_dispatcher.py`, `*_workflow.py`) | Yes — affected level(s) |
| PR modifies an intent detector (`*_intent.py`) | Yes — affected level(s) |
| PR modifies `docs/` only | No |
| PR modifies `agent/tests/` only (no runtime change) | No |
| PR modifies `agent/src/swarm/` | Yes — Level 4 |

---

## Mandatory PR-FLOW Evidence Format

Every PR description or commit message must include this block:

```
Nível de risco: [1|2|3|4]
Justificativa: <uma linha>
Evidência:
  SEALED N1: [X passed | NÃO EXECUTADO — <motivo>]
  SEALED N2: [X passed | NÃO EXECUTADO — <motivo>]
  SEALED N3: [X passed | NÃO EXECUTADO — <motivo>]
  SEALED N4: [X passed | NÃO EXECUTADO — <motivo>]
  Docs anti-drift: [X passed | NÃO EXECUTADO — <motivo>]
  Unit suite: [X passed | NÃO EXECUTADO — <motivo>]
  Runtime smoke: [PASS — <nível> | NÃO EXECUTADO — <motivo>]
```

**Example — doc-only PR (Nível 2):**
```
Nível de risco: 2
Justificativa: doc operacional, sem alteração de runtime
Evidência:
  SEALED N1: NÃO EXECUTADO — PR doc-only, sem alteração de dispatcher
  SEALED N2: NÃO EXECUTADO — PR doc-only, sem alteração de dispatcher
  SEALED N3: NÃO EXECUTADO — PR doc-only, sem alteração de dispatcher
  SEALED N4: NÃO EXECUTADO — PR doc-only, sem alteração de dispatcher
  Docs anti-drift: 13 passed
  Unit suite: NÃO EXECUTADO — PR doc-only
  Runtime smoke: NÃO EXECUTADO — PR doc-only
```

**Example — dispatcher change (Nível 3-4):**
```
Nível de risco: 4
Justificativa: alteração em SwarmWorkflowDispatcher — contrato SEALED
Evidência:
  SEALED N1: 21 passed
  SEALED N2: 21 passed
  SEALED N3: 21 passed
  SEALED N4: 21 passed
  Docs anti-drift: 20 passed
  Unit suite: 208 passed
  Runtime smoke: PASS — Level 4 (swarm, 4/4 agents, iterations=0)
```

---

## Rule: NÃO EXECUTADO

`NÃO EXECUTADO` is a valid declaration. It means:

> "This gate was consciously skipped because the PR does not touch the relevant
> scope. The skip is intentional and documented."

`NÃO EXECUTADO` **requires a reason**. The reason must explain why the gate is
out of scope for this PR — not just "skipped" or "n/a".

`NÃO EXECUTADO` is **not acceptable** when:
- The PR modifies a dispatcher, workflow, or intent detector.
- The PR modifies `loop.py`.
- The PR adds or changes a SEALED baseline.
- The PR changes any code under `agent/src/`.

Declaring a gate as passed without running it — **fingir execução** — is a
hard policy violation. It defeats the purpose of this runbook.

---

## Residual Risks of Operating Without Remote CI

Operating without remote CI is a deliberate trade-off. These risks remain:

| Risk | Mitigation |
|---|---|
| Human error — gate not run despite policy | PR-FLOW evidence block is mandatory; reviewer must challenge undeclared gates |
| Environment drift — .venv-test out of sync with Docker | Run smokes in Docker for dispatcher changes; do not rely solely on .venv-test |
| Flaky local tests masked by re-run | Do not re-run a failing test without understanding the failure; document flakiness |
| Contributor forgets to update SEALED canaries | SEALED canary tests catch regression on next gate run; fail loudly |
| No automatic gate on new branch push | Discipline: run gates before opening PR, not after |

Remote CI should be re-evaluated when operational cost decreases (e.g., self-hosted
runner, faster smoke, reduced API cost). Until then, this runbook is the gate.

---

## Reference

- Dispatcher stack: [BEGINNER_TRAIL.md](BEGINNER_TRAIL.md)
- Demo sequence and PASS/FAIL per level: [DEMO_READINESS_CHECKLIST.md](DEMO_READINESS_CHECKLIST.md)
- SEALED baseline docs: `MARKET_DATA_ROUTING_BASELINE.md`, `CANDLESTICK_WORKFLOW_BASELINE.md`,
  `BACKTEST_WORKFLOW_BASELINE.md`, `SWARM_WORKFLOW_BASELINE.md`
