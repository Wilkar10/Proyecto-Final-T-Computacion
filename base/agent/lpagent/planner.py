"""Quién ELIGE qué pedidos van en el viaje. Nunca decide el recorrido: eso lo hace el solver y lo verifica V."""
from __future__ import annotations

import json
from dataclasses import dataclass

from .grid import distance_matrix
from .models import BATTERY_PER_COST, MIN_BATTERY, Context, Robot, Stop, TripProblem
from .validator import MAX_STOPS, verify_proposal


@dataclass
class Selection:
    robot: Robot
    stops: list[Stop]
    rationale: str
    source: str  # rule | llm


def build_problem(ctx: Context, robot: Robot, stops: list[Stop]) -> TripProblem:
    points = [ctx.origin] + [(s.x, s.y) for s in stops]
    budget = int((robot.battery - MIN_BATTERY) // BATTERY_PER_COST)
    return TripProblem(list(stops), distance_matrix(ctx.grid_rows, points), max(budget, 0))


def pick_robot(ctx: Context) -> Robot | None:
    ready = [r for r in ctx.robots if r.status == "IDLE" and r.battery > MIN_BATTERY]
    return max(ready, key=lambda r: (r.battery, r.code), default=None) if ready else None


class RulePlanner:
    """Voraz por prioridad: agrega pedidos en orden de prioridad mientras el solver confirme que aún cabe en la batería."""

    def __init__(self, solver, time_limit_s: float = 2.0):
        self.solver, self.time_limit_s = solver, time_limit_s

    def select(self, ctx: Context) -> Selection | None:
        robot = pick_robot(ctx)
        if robot is None or not ctx.orders:
            return None
        chosen: list[Stop] = []
        for cand in sorted(ctx.orders, key=lambda s: (-s.priority, s.code)):
            if len(chosen) >= MAX_STOPS:
                break
            try:
                problem = build_problem(ctx, robot, chosen + [cand])
            except ValueError:
                continue  # destino inalcanzable en el plano
            if self.solver.solve(problem, self.time_limit_s).feasible:
                chosen.append(cand)
        if not chosen:
            return None
        return Selection(robot, chosen, f"{len(chosen)} pedidos por prioridad que caben en la batería de {robot.code}", "rule")


TOOLS = [
    {"name": "list_orders", "description": "Pedidos CREATED con destino y prioridad (solo lectura).",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "list_robots", "description": "Robots con batería y estado (solo lectura).",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "check_trip", "description": "Comprueba si un conjunto de pedidos cabe en la batería de un robot. Usa el solver y el validador.",
     "input_schema": {"type": "object", "required": ["robot_code", "order_codes"],
                      "properties": {"robot_code": {"type": "string"}, "order_codes": {"type": "array", "items": {"type": "string"}}}}},
    {"name": "propose_trip", "description": "Termina: propone el viaje. Una persona lo aprobará.",
     "input_schema": {"type": "object", "required": ["robot_code", "order_codes", "rationale"],
                      "properties": {"robot_code": {"type": "string"}, "order_codes": {"type": "array", "items": {"type": "string"}},
                                     "rationale": {"type": "string"}}}},
]

SYSTEM = ("Eres el asistente de despacho de LOGISTPULSE. SOLO sugieres: una persona aprueba. "
          "Elige un robot libre y un conjunto de pedidos que quepa en su batería, priorizando los más urgentes. "
          "No inventes códigos: usa las herramientas de lectura. Verifica con check_trip antes de proponer. "
          "El orden del recorrido lo calcula el sistema, no tú. Termina llamando a propose_trip.")


class LLMPlanner:
    """Bucle de herramientas con un modelo de lenguaje. Límites: max_steps; entradas validadas contra el contexto real."""

    def __init__(self, client, solver, max_steps: int = 8, time_limit_s: float = 2.0):
        self.client, self.solver, self.max_steps, self.time_limit_s = client, solver, max_steps, time_limit_s

    def select(self, ctx: Context) -> Selection | None:
        by_code = {o.code: o for o in ctx.orders}
        robots = {r.code: r for r in ctx.robots}
        messages: list[dict] = [{"role": "user", "content": "Planifica el siguiente viaje."}]

        def run_tool(name: str, args: dict) -> dict:
            if name == "list_orders":
                return {"orders": [{"code": o.code, "x": o.x, "y": o.y, "priority": o.priority} for o in ctx.orders]}
            if name == "list_robots":
                return {"robots": [{"code": r.code, "battery": r.battery, "status": r.status} for r in ctx.robots]}
            if name == "check_trip":
                err = self._validate_args(args, by_code, robots)
                if err:
                    return {"error": err}
                robot, stops = robots[args["robot_code"]], [by_code[c] for c in args["order_codes"]]
                try:
                    problem = build_problem(ctx, robot, stops)
                except ValueError as e:
                    return {"error": str(e)}
                sol = self.solver.solve(problem, self.time_limit_s)
                ok, errs = verify_proposal(problem, sol.tour or [], robot, args["order_codes"]) if sol.feasible else (False, [sol.note])
                return {"feasible": ok, "budget": problem.budget, "cost": sol.cost, "proven": sol.proven, "errors": errs}
            return {"error": f"herramienta desconocida: {name}"}

        for _ in range(self.max_steps):
            blocks = self.client.complete(SYSTEM, messages, TOOLS)
            messages.append({"role": "assistant", "content": blocks})
            calls = [b for b in blocks if b.get("type") == "tool_use"]
            if not calls:
                return None  # el modelo no propuso nada
            results = []
            for call in calls:
                if call["name"] == "propose_trip":
                    args = call["input"]
                    err = self._validate_args(args, by_code, robots)
                    if err:
                        results.append({"type": "tool_result", "tool_use_id": call["id"], "content": json.dumps({"error": err})})
                        continue
                    return Selection(robots[args["robot_code"]], [by_code[c] for c in args["order_codes"]],
                                     str(args.get("rationale", ""))[:500], "llm")
                results.append({"type": "tool_result", "tool_use_id": call["id"],
                                "content": json.dumps(run_tool(call["name"], call.get("input", {})), ensure_ascii=False)})
            messages.append({"role": "user", "content": results})
        return None  # límite de pasos

    @staticmethod
    def _validate_args(args: dict, by_code: dict, robots: dict) -> str | None:
        if args.get("robot_code") not in robots:
            return f"robot desconocido: {args.get('robot_code')!r}"
        codes = args.get("order_codes")
        if not isinstance(codes, list) or not codes:
            return "order_codes debe ser una lista no vacía"
        unknown = [c for c in codes if c not in by_code]
        if unknown:
            return f"pedidos desconocidos o ya despachados: {unknown}"
        return None
