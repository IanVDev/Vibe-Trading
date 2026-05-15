"""Deterministic swarm workflow dispatcher (Patch 9).

Intercepts named-preset swarm prompts before the ReAct/LLM loop and
invokes run_swarm directly via the tool registry. The LLM is never called.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from src.agent.swarm_intent import SwarmIntent, detect_swarm_intent
from src.agent.market_data_dispatcher import _sanitize


def _trace(trace: Any, event_type: str, **kwargs: Any) -> None:
    trace.write({"event": event_type, "type": event_type, **kwargs})


class SwarmWorkflowDispatcher:
    ROUTED_BY = "swarm_workflow"

    def try_route(
        self,
        user_message: str,
        registry: Any,
        trace: Any,
    ) -> Optional[dict]:
        intent = detect_swarm_intent(user_message)
        if intent is None:
            return None

        _trace(trace, "router", name=self.ROUTED_BY, intent={
            "preset_name": intent.preset_name,
            "target": intent.target,
            "timeframe": intent.timeframe,
        })

        _trace(trace, "tool_call", name="run_swarm", args={"prompt": user_message})

        try:
            raw = registry.execute("run_swarm", {"prompt": user_message})
        except Exception as exc:
            return self._fail(_sanitize(str(exc)), "run_swarm_exception", trace)

        _trace(trace, "tool_result", name="run_swarm")

        try:
            result = json.loads(raw) if isinstance(raw, str) else raw
        except (json.JSONDecodeError, TypeError):
            return self._fail("unparseable run_swarm result", "parse_error", trace)

        status = result.get("status", "")
        if status not in ("completed",):
            reason = _sanitize(result.get("error") or f"run_swarm status={status}")
            return self._fail(reason, "run_swarm_not_completed", trace)

        final_report = result.get("final_report") or ""
        if not final_report.strip():
            return self._fail("final_report is empty", "report_missing", trace)

        tasks = result.get("tasks") or []
        completed_tasks = [t for t in tasks if t.get("status") == "completed"]
        if not completed_tasks:
            return self._fail("no agent tasks completed", "agents_not_executed", trace)

        _trace(trace, "workflow_step", name="validate_report",
               task_count=len(tasks), completed=len(completed_tasks))
        _trace(trace, "answer")
        _trace(trace, "end", status="success", iterations=0, routed_by=self.ROUTED_BY)

        return {
            "status": "success",
            "content": final_report,
            "iterations": 0,
            "routed_by": self.ROUTED_BY,
            "run_id": result.get("run_id", ""),
            "preset": result.get("preset", intent.preset_name),
            "task_count": len(tasks),
        }

    @staticmethod
    def _fail(reason: str, step: str, trace: Any) -> dict:
        _trace(trace, "end", status="failed", step=step, reason=reason)
        return {
            "status": "failed",
            "content": f"Swarm falhou: {reason}",
            "iterations": 0,
            "routed_by": SwarmWorkflowDispatcher.ROUTED_BY,
        }
