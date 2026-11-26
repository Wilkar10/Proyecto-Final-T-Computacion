"""Orquestación del agente (autonomía nivel 1 de 4: SUGIERE; una persona aprueba).
Flujo: contexto -> selección (regla o LLM) -> solver -> validador determinista -> (fallback) -> propuesta pendiente."""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from .audit import Audit
from .models import Proposal
from .planner import RulePlanner, Selection, build_problem
from .validator import verify_proposal


class DispatchAgent:
    def __init__(self, data, solver, actuator, audit: Audit, planner=None, time_limit_s: float = 2.0, max_seconds: float = 20.0):
        self.data, self.solver, self.actuator, self.audit = data, solver, actuator, audit
        self.fallback = RulePlanner(solver, time_limit_s)
        self.planner = planner or self.fallback
        self.time_limit_s, self.max_seconds = time_limit_s, max_seconds
        self.proposals: dict[str, Proposal] = {}

    # ------------------------------------------------------------------ planificar (NO ejecuta nada)
    def plan(self) -> tuple[Proposal | None, str]:
        t0 = time.monotonic()
        ctx = self.data.load_context()
        self.audit.log("plan_started", orders=len(ctx.orders), robots=len(ctx.robots))
        sel, source = self._select(self.planner, ctx), self.planner.__class__.__name__
        proposal, reason = self._finalize(ctx, sel)
        if proposal is None and self.planner is not self.fallback:
            self.audit.log("fallback_used", reason=reason, planner=source)
            sel = self._select(self.fallback, ctx)
            proposal, reason = self._finalize(ctx, sel, source_override="fallback")
        if time.monotonic() - t0 > self.max_seconds:
            self.audit.log("plan_slow", seconds=round(time.monotonic() - t0, 2))
        if proposal is None:
            self.audit.log("no_proposal", reason=reason)
            return None, reason
        self.proposals[proposal.proposal_id] = proposal
        self.audit.log("proposal_created", proposal=proposal.__dict__)
        return proposal, "ok"

    def _select(self, planner, ctx) -> Selection | None:
        try:
            return planner.select(ctx)
        except Exception as exc:  # un planificador defectuoso nunca debe tumbar el flujo
            self.audit.log("planner_error", planner=planner.__class__.__name__, error=repr(exc))
            return None

    def _finalize(self, ctx, sel: Selection | None, source_override: str | None = None):
        if sel is None:
            return None, "el planificador no propuso un viaje"
        try:
            problem = build_problem(ctx, sel.robot, sel.stops)
        except ValueError as exc:
            return None, str(exc)
        solution = self.solver.solve(problem, self.time_limit_s)
        self.audit.log("solver_result", algorithm=solution.algorithm, feasible=solution.feasible, proven=solution.proven, cost=solution.cost)
        if not solution.feasible or solution.tour is None:
            return None, solution.note or "el solver no halló un recorrido dentro del presupuesto"
        codes = [sel.stops[i - 1].code for i in solution.tour]  # orden del recorrido
        ok, errors = verify_proposal(problem, solution.tour, sel.robot, [s.code for s in sel.stops])
        self.audit.log("validation", ok=ok, errors=errors)
        if not ok:
            return None, "; ".join(errors)
        return Proposal(
            proposal_id=uuid.uuid4().hex[:12], robot=sel.robot.code, order_codes=codes,
            cost=int(solution.cost), budget=problem.budget, battery_before=sel.robot.battery,
            algorithm=solution.algorithm, exact=solution.proven, rationale=sel.rationale,
            source=source_override or sel.source, created_at=datetime.now(timezone.utc).isoformat()), "ok"

    # ------------------------------------------------------------------ decisión humana
    def decide(self, proposal_id: str, approver: str, approve: bool) -> Proposal:
        if not approver or not approver.strip():
            raise PermissionError("se requiere identificar a quien aprueba (X-Approver)")
        p = self.proposals.get(proposal_id)
        if p is None:
            raise KeyError(proposal_id)
        if p.status != "PENDING_APPROVAL":
            raise ValueError(f"la propuesta ya está {p.status}")
        p.decided_by = approver.strip()
        if not approve:
            p.status = "REJECTED"
            self.audit.log("rejected", proposal_id=p.proposal_id, by=p.decided_by)
            return p
        p.status = "APPROVED"
        self.audit.log("approved", proposal_id=p.proposal_id, by=p.decided_by)
        try:
            p.detail = self.actuator.execute(p)
            p.status = "EXECUTED"
        except Exception as exc:
            p.status, p.detail = "FAILED", {"error": str(exc)}
        self.audit.log("executed", proposal_id=p.proposal_id, status=p.status, detail=p.detail)
        return p
