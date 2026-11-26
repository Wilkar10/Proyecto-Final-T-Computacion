"""Adaptadores BASE (los que entrega el docente). Cada deber puede reemplazar uno vía variable de entorno:
   LP_SOLVER_PLUGIN / LP_DATA_PLUGIN / LP_ACTUATOR_PLUGIN / LP_AUDIT_PLUGIN = "paquete.modulo:funcion_build"
"""
from __future__ import annotations

import itertools
import json
import os
import time
from pathlib import Path

from .grid import DEFAULT_LAYOUT
from .labclient import LabClient
from .models import Context, Proposal, Robot, Solution, Stop, TripProblem


# --------------------------------------------------------------------------- Solver (Teoría)
class BaselineSolver:
    """Exacto por fuerza bruta si n <= 8 (O(n!·n)); si no, vecino más cercano (heurística, sin garantía).
    El deber de Teoría lo reemplaza por Held-Karp, 2-opt, etc. con medición y verificador propio."""
    name = "baseline"
    EXACT_MAX_N = 8

    def solve(self, problem: TripProblem, time_limit_s: float = 2.0) -> Solution:
        n = problem.n
        if n == 0:
            return Solution(True, [], 0, "trivial", True)
        if n <= self.EXACT_MAX_N:
            best, best_cost = None, None
            deadline = time.monotonic() + time_limit_s
            for perm in itertools.permutations(range(1, n + 1)):
                c = problem.tour_cost(list(perm))
                if best_cost is None or c < best_cost:
                    best, best_cost = list(perm), c
                if time.monotonic() > deadline:
                    return Solution(False, None, None, "brute_force", False, "tiempo agotado")
            ok = best_cost is not None and best_cost <= problem.budget
            return Solution(ok, best if ok else None, best_cost if ok else None, "brute_force", True,
                            "" if ok else f"el mínimo {best_cost} excede el presupuesto {problem.budget}")
        # Heurística voraz
        left, cur, order = set(range(1, n + 1)), 0, []
        while left:
            nxt = min(left, key=lambda j: problem.dist[cur][j])
            order.append(nxt)
            left.remove(nxt)
            cur = nxt
        c = problem.tour_cost(order)
        ok = c <= problem.budget
        return Solution(ok, order if ok else None, c if ok else None, "nearest_neighbor", False,
                        "" if ok else "la heurística no halló un ciclo dentro del presupuesto (no prueba que no exista)")


# --------------------------------------------------------------------------- Datos (Bases de Datos)
class FixtureData:
    """Lee un snapshot JSON (por defecto fixtures/lab_snapshot.json). No necesita red ni base de datos."""

    def __init__(self, path: str | None = None):
        p = Path(path or os.getenv("LP_FIXTURE", Path(__file__).resolve().parent.parent / "fixtures" / "lab_snapshot.json"))
        self._raw = json.loads(p.read_text(encoding="utf-8"))

    def load_context(self) -> Context:
        raw = self._raw
        orders = [Stop(o["code"], o["destX"], o["destY"], self.priority_of(o.get("customer", ""))) for o in raw["orders"]]
        robots = [Robot(r["code"], r["x"], r["y"], r["battery"], r.get("status", "IDLE")) for r in raw["robots"]]
        return Context(raw.get("grid", DEFAULT_LAYOUT), robots, orders, tuple(raw.get("origin", (0, 0))))

    def priority_of(self, customer: str) -> float:
        return float(self._raw.get("priorities", {}).get(customer, 1.0))


class LabData(FixtureData):
    """Lee pedidos CREATED, robots y plano desde la API viva del lab. La prioridad viene del fixture (o del
    adaptador de Bases de Datos si se configura LP_DATA_PLUGIN)."""

    def __init__(self, client: LabClient | None = None, priorities=None):
        self.client = client or LabClient()
        self._priorities = priorities  # callable(customer)->float | None
        self._raw = {"priorities": {}}

    def priority_of(self, customer: str) -> float:
        return float(self._priorities(customer)) if self._priorities else 1.0

    def load_context(self) -> Context:
        page = self.client.get("/api/orders?status=CREATED&page=0&size=100")
        robots = self.client.get("/api/robots")
        grid = self.client.get("/api/routes/grid")["rows"]
        orders = [Stop(o["code"], o["destX"], o["destY"], self.priority_of(o["customer"])) for o in page["content"]]
        rs = [Robot(r["code"], r["x"], r["y"], r["battery"], r["status"]) for r in robots]
        return Context(grid, rs, orders, (0, 0))


# --------------------------------------------------------------------------- Actuador (Desarrollo de SW)
class DryRunActuator:
    """No toca ningún sistema: solo describe lo que haría. Es el actuador por defecto (seguro)."""

    def execute(self, proposal: Proposal) -> dict:
        return {"mode": "dry-run", "would_dispatch": proposal.order_codes, "robot": proposal.robot}


class LabActuator:
    """Ejecuta una propuesta APROBADA contra la API del lab, un pedido a la vez y en el orden del recorrido.
    LIMITACIÓN: el endpoint /dispatch elige el robot él mismo, por lo que no garantiza el recorrido multi-parada.
    Para viajes atómicos e idempotentes use lp_dsm.actuator:build (POST /api/trips)."""

    def __init__(self, client: LabClient | None = None):
        self.client = client or LabClient()

    def execute(self, proposal: Proposal) -> dict:
        page = self.client.get("/api/orders?status=CREATED&page=0&size=100")
        ids = {o["code"]: o["id"] for o in page["content"]}
        results = []
        for code in proposal.order_codes:
            if code not in ids:
                results.append({"order": code, "error": "ya no está en estado CREATED"})
                continue
            res = self.client.post(f"/api/orders/{ids[code]}/dispatch")
            results.append({"order": code, "robot": res.get("robot"), "status": res.get("status")})
        return {"mode": "lab", "results": results}
