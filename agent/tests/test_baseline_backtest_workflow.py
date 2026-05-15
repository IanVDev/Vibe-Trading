"""SEALED baseline canary for Level 3 Backtest Workflow.

Risk level: 4 (SEALED). Protects the public contract of the deterministic
backtest workflow established by Patch 7. Five classes:

  A. Document  — docs/BACKTEST_WORKFLOW_BASELINE.md is intact.
  B. Surface   — code modules / classes / template / loop integration.
  C. Workflow  — dispatch order, metrics from CSV, no LLM.
  D. Out-of-scope — market data / candlestick / swarm / generic / ambiguous
                    backtest fall through.
  E. Fail-closed — sanitised errors, no web, no LLM fallback.

Failure here means a Level 3 baseline regression.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

_BASELINE_DOC = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "BACKTEST_WORKFLOW_BASELINE.md"
)

_INVARIANT_SUBSTRINGS = (
    "Objective: deterministic pre-LLM workflow for simple MA-crossover backtest",
    "Simple MA-crossover backtest prompts are intercepted before the LLM/ReAct loop",
    "`backtest_workflow` is the deterministic entrypoint",
    "`signal_engine.py` is generated from a fixed template, never by the LLM",
    "The LLM does not decide the first action for simple MA-crossover backtest",
    "Dispatch order: `write_config` → `write_signal_engine` → `backtest` → `read_metrics` → `answer`",
    "Required metrics: Sharpe ratio, max drawdown, total return, number of trades",
    "Metrics must come from `artifacts/metrics.csv`",
    "`web_search`, `read_url` and `browser` are forbidden",
    "LLM fallback is forbidden",
    "Raw tracebacks are forbidden in any error path",
    "Invented metrics are a regression",
    "Baseline = Patch 7",
    "Level 3 Backtest Workflow — SEALED",
)

_SECRET_SHAPED_BLOCKLIST = (
    "Authorization:", "Bearer ", "token=", "api_key=",
    "secret-", "Traceback", "internal://", "/Users/", "/home/",
    "proxy.local:",
)

_CANONICAL_PROMPT = (
    "Backtest a simple moving-average crossover strategy on BTC-USDT:\n"
    "- Buy when 20-day MA crosses above 50-day MA\n"
    "- Sell when 20-day MA crosses below 50-day MA\n"
    "- Period: 2023-01-01 to 2024-12-31\n"
    "- Initial capital: 10000 USDT\n"
    "Report Sharpe ratio, max drawdown, total return, and number of trades."
)


# --- Class A: Document -------------------------------------------------------

@pytest.mark.unit
def test_baseline_doc_exists() -> None:
    assert _BASELINE_DOC.is_file(), (
        f"Baseline document missing at {_BASELINE_DOC}. "
        "Level 3 Backtest Workflow cannot be SEALED without it."
    )


@pytest.mark.unit
def test_baseline_doc_contains_all_invariant_substrings() -> None:
    text = _BASELINE_DOC.read_text(encoding="utf-8")
    missing = [s for s in _INVARIANT_SUBSTRINGS if s not in text]
    assert not missing, f"Baseline doc is missing invariant substrings: {missing}"


@pytest.mark.unit
def test_baseline_doc_does_not_leak_secrets() -> None:
    text = _BASELINE_DOC.read_text(encoding="utf-8")
    found = [s for s in _SECRET_SHAPED_BLOCKLIST if s in text]
    assert not found, (
        f"Baseline doc contains secret-shaped substrings: {found}."
    )


@pytest.mark.unit
def test_baseline_doc_starts_and_ends_with_sealed_marker() -> None:
    text = _BASELINE_DOC.read_text(encoding="utf-8").strip()
    marker = "Level 3 Backtest Workflow — SEALED"
    first = text.splitlines()[0]
    assert marker in first, f"First line must be the SEALED marker: '{first}'"
    assert text.endswith(marker), (
        f"Last line must be the SEALED marker: '{text.splitlines()[-1]}'"
    )


# --- Class B: Surface --------------------------------------------------------

@pytest.mark.unit
def test_module_backtest_intent_exports_detector() -> None:
    from src.agent.backtest_intent import (
        BacktestIntent,
        detect_backtest_intent,
    )

    assert callable(detect_backtest_intent)
    fields = BacktestIntent.__dataclass_fields__
    for f in ("symbol", "fast_window", "slow_window", "start_date", "end_date",
              "initial_capital", "strategy_type"):
        assert f in fields, f"Missing field {f!r} on BacktestIntent"


@pytest.mark.unit
def test_module_backtest_workflow_exports_class() -> None:
    from src.agent.backtest_workflow import BacktestWorkflowDispatcher

    assert BacktestWorkflowDispatcher.ROUTED_BY == "backtest_workflow"
    assert callable(BacktestWorkflowDispatcher().try_route)


@pytest.mark.unit
def test_backtest_workflow_has_fixed_template() -> None:
    from src.agent.backtest_workflow import _MA_CROSSOVER_TEMPLATE

    assert "class SignalEngine" in _MA_CROSSOVER_TEMPLATE
    assert "def generate" in _MA_CROSSOVER_TEMPLATE
    assert "{fast_window}" in _MA_CROSSOVER_TEMPLATE
    assert "{slow_window}" in _MA_CROSSOVER_TEMPLATE
    assert "import pandas as pd" in _MA_CROSSOVER_TEMPLATE
    assert "eval(" not in _MA_CROSSOVER_TEMPLATE
    assert "exec(" not in _MA_CROSSOVER_TEMPLATE
    assert "subprocess" not in _MA_CROSSOVER_TEMPLATE


@pytest.mark.unit
def test_loop_integrates_backtest_workflow() -> None:
    """AgentLoop must reference BacktestWorkflowDispatcher. If someone
    deletes the integration, this canary fails before the runtime regresses."""
    from src.agent import loop as loop_module

    source = Path(loop_module.__file__).read_text(encoding="utf-8")
    assert "BacktestWorkflowDispatcher" in source, (
        "AgentLoop no longer references BacktestWorkflowDispatcher — "
        "Patch 7 integration has been removed."
    )
    # Level 1 SEALED defence in depth.
    assert "MarketDataDispatcher" in source, (
        "AgentLoop no longer references MarketDataDispatcher — Level 1 "
        "SEALED contract regressed."
    )
    # Level 2 SEALED defence in depth.
    assert "CandlestickWorkflowDispatcher" in source, (
        "AgentLoop no longer references CandlestickWorkflowDispatcher — "
        "Level 2 SEALED contract regressed."
    )
    # Ordering: market_data first, candlestick second, backtest third.
    idx_md = source.index("MarketDataDispatcher().try_route")
    idx_cs = source.index("CandlestickWorkflowDispatcher().try_route")
    idx_bt = source.index("BacktestWorkflowDispatcher().try_route")
    assert idx_md < idx_cs < idx_bt, (
        "Dispatcher order in loop.py must be MarketData → Candlestick → Backtest"
    )


# --- Class C: Workflow -------------------------------------------------------

def _write_metrics_csv(run_dir: Path, sharpe: float = 1.42,
                       max_dd: float = -0.18, total_return: float = 0.53,
                       trade_count: int = 47) -> None:
    artifacts = run_dir / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    with (artifacts / "metrics.csv").open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["sharpe", "max_drawdown", "total_return", "trade_count"])
        writer.writerow([sharpe, max_dd, total_return, trade_count])


def _registry_ok(run_dir: Path) -> MagicMock:
    _write_metrics_csv(run_dir)
    reg = MagicMock()

    def _execute(name: str, args: dict) -> str:
        if name == "backtest":
            return json.dumps({"status": "ok", "run_dir": args["run_dir"]})
        return json.dumps({"status": "error", "error": f"unexpected tool: {name}"})

    reg.execute = MagicMock(side_effect=_execute)
    return reg


def _trace_sink() -> tuple[MagicMock, list[dict[str, Any]]]:
    events: list[dict[str, Any]] = []
    trace = MagicMock()
    trace.write = MagicMock(side_effect=lambda evt: events.append(evt))
    return trace, events


@pytest.mark.unit
def test_workflow_dispatch_order_is_canonical(tmp_path: Path) -> None:
    from src.agent.backtest_workflow import BacktestWorkflowDispatcher

    reg = _registry_ok(tmp_path)
    trace, events = _trace_sink()
    result = BacktestWorkflowDispatcher().try_route(
        _CANONICAL_PROMPT, reg, trace, str(tmp_path),
    )
    assert result is not None and result["status"] == "success"

    ordered = [(e.get("event"), e.get("name", "")) for e in events]
    expected = [
        ("router", "backtest_workflow"),
        ("workflow_step", "write_config"),
        ("workflow_step", "write_signal_engine"),
        ("tool_call", "backtest"),
        ("tool_result", "backtest"),
        ("workflow_step", "read_metrics"),
        ("answer", ""),
        ("end", ""),
    ]
    assert ordered == expected, f"Unexpected dispatch order: {ordered}"


@pytest.mark.unit
def test_workflow_metrics_are_read_from_csv(tmp_path: Path) -> None:
    from src.agent.backtest_workflow import BacktestWorkflowDispatcher

    _write_metrics_csv(tmp_path, sharpe=2.1, max_dd=-0.09,
                       total_return=0.77, trade_count=31)
    reg = MagicMock()
    reg.execute = MagicMock(return_value=json.dumps({"status": "ok"}))
    trace, _ = _trace_sink()
    result = BacktestWorkflowDispatcher().try_route(
        _CANONICAL_PROMPT, reg, trace, str(tmp_path),
    )
    assert result is not None and result["status"] == "success"
    assert result["sharpe"] == pytest.approx(2.1)
    assert result["max_drawdown"] == pytest.approx(-0.09)
    assert result["total_return"] == pytest.approx(0.77)
    assert result["trade_count"] == 31


@pytest.mark.unit
def test_workflow_metrics_are_validated_as_numeric(tmp_path: Path) -> None:
    from src.agent.backtest_workflow import BacktestWorkflowDispatcher

    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "metrics.csv").write_text(
        "sharpe,max_drawdown,total_return,trade_count\nNA,NA,NA,NA\n",
        encoding="utf-8",
    )
    reg = MagicMock()
    reg.execute = MagicMock(return_value=json.dumps({"status": "ok"}))
    trace, _ = _trace_sink()
    result = BacktestWorkflowDispatcher().try_route(
        _CANONICAL_PROMPT, reg, trace, str(tmp_path),
    )
    assert result is not None and result["status"] == "failed"


@pytest.mark.unit
def test_workflow_does_not_call_llm(tmp_path: Path) -> None:
    from src.agent.backtest_workflow import BacktestWorkflowDispatcher

    reg = _registry_ok(tmp_path)
    trace, _ = _trace_sink()
    result = BacktestWorkflowDispatcher().try_route(
        _CANONICAL_PROMPT, reg, trace, str(tmp_path),
    )
    assert result is not None and result.get("iterations") == 0
    assert result.get("routed_by") == "backtest_workflow"


# --- Class D: Out-of-scope ---------------------------------------------------

@pytest.mark.unit
@pytest.mark.parametrize("prompt", [
    # Level 1 territory — simple market data
    "What is the current price of BTC-USDT?",
    # Level 2 territory — candlestick analysis
    "Analyze the candlestick patterns on BTC-USDT daily for the last 60 days",
    # Swarm — different feature surface
    "Run the crypto_research_lab swarm on ETH-USDT",
    # Generic strategy — too open-ended
    "Build me a strategy on BTC-USDT",
    # Ambiguous backtest — no dates or capital
    "Backtest a moving-average crossover on BTC-USDT",
    # Backtest with non-MA strategy
    "Backtest an RSI strategy on BTC-USDT from 2023-01-01 to 2024-12-31 with 10000 USDT",
])
def test_out_of_scope_prompts_not_intercepted(tmp_path: Path, prompt: str) -> None:
    from src.agent.backtest_workflow import BacktestWorkflowDispatcher

    reg = _registry_ok(tmp_path)
    trace, _ = _trace_sink()
    result = BacktestWorkflowDispatcher().try_route(
        prompt, reg, trace, str(tmp_path),
    )
    assert result is None, (
        f"Out-of-scope prompt was incorrectly intercepted: {prompt!r}"
    )
    # Backtest tool must not have been called.
    names = [c.args[0] for c in reg.execute.call_args_list]
    assert "backtest" not in names


# --- Class E: Fail-closed ----------------------------------------------------

@pytest.mark.unit
def test_backtest_engine_failure_is_sanitised(tmp_path: Path) -> None:
    from src.agent.backtest_workflow import BacktestWorkflowDispatcher

    poisoned = json.dumps({
        "status": "error",
        "error": (
            "Authorization: Bearer secret-xyz Traceback "
            "internal://proxy.local:9090/leak /Users/ian /home/x "
            "token=abc api_key=APIKEY1"
        ),
    })
    reg = MagicMock()
    reg.execute = MagicMock(return_value=poisoned)
    trace, _ = _trace_sink()
    result = BacktestWorkflowDispatcher().try_route(
        _CANONICAL_PROMPT, reg, trace, str(tmp_path),
    )
    assert result is not None and result["status"] == "failed"
    content = result["content"]
    leaks = [s for s in _SECRET_SHAPED_BLOCKLIST if s in content]
    assert not leaks, f"Sanitisation failed; leaked: {leaks!r}"
    # No metrics in result on failure path.
    assert "sharpe" not in result


@pytest.mark.unit
def test_missing_metrics_csv_fails_closed(tmp_path: Path) -> None:
    from src.agent.backtest_workflow import BacktestWorkflowDispatcher

    reg = MagicMock()
    reg.execute = MagicMock(return_value=json.dumps({"status": "ok"}))
    trace, _ = _trace_sink()
    result = BacktestWorkflowDispatcher().try_route(
        _CANONICAL_PROMPT, reg, trace, str(tmp_path),
    )
    assert result is not None and result["status"] == "failed"
    assert "metrics.csv" in result["content"]
    for bad in _SECRET_SHAPED_BLOCKLIST:
        assert bad not in result["content"]


@pytest.mark.unit
def test_no_web_tools_invoked_on_any_path(tmp_path: Path) -> None:
    from src.agent.backtest_workflow import BacktestWorkflowDispatcher

    # Success path.
    reg_ok = _registry_ok(tmp_path)
    trace_ok, _ = _trace_sink()
    BacktestWorkflowDispatcher().try_route(
        _CANONICAL_PROMPT, reg_ok, trace_ok, str(tmp_path),
    )

    # Failure path.
    reg_fail = MagicMock()
    reg_fail.execute = MagicMock(
        return_value=json.dumps({"status": "error", "error": "boom"})
    )
    trace_fail, _ = _trace_sink()
    BacktestWorkflowDispatcher().try_route(
        _CANONICAL_PROMPT, reg_fail, trace_fail, str(tmp_path),
    )

    for reg in (reg_ok, reg_fail):
        names = [c.args[0] for c in reg.execute.call_args_list]
        assert "web_search" not in names
        assert "read_url" not in names
        assert "browser" not in names


@pytest.mark.unit
def test_no_llm_fallback_on_failure(tmp_path: Path) -> None:
    from src.agent.backtest_workflow import BacktestWorkflowDispatcher

    # Even when backtest fails, result must have iterations=0 and
    # routed_by=backtest_workflow — no LLM was consulted.
    reg = MagicMock()
    reg.execute = MagicMock(
        return_value=json.dumps({"status": "error", "error": "engine down"})
    )
    trace, _ = _trace_sink()
    result = BacktestWorkflowDispatcher().try_route(
        _CANONICAL_PROMPT, reg, trace, str(tmp_path),
    )
    assert result is not None
    assert result["status"] == "failed"
    assert result["iterations"] == 0
    assert result["routed_by"] == "backtest_workflow"
