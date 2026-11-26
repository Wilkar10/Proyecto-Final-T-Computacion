"""STRATEGY — política de selección de pedidos intercambiable en tiempo de ejecución.
Problema: «¿qué pedidos intentamos meter primero?» es una decisión de NEGOCIO que cambia (urgencia, cercanía, rendimiento).
Contexto: PolicyPlanner (cumple el contrato de planner: select(ctx) -> Selection). Estrategias: orden de candidatos."""
from __future__ import annotations

from typing import Protocol

from lpagent.models import Context, Robot, Stop
from lpagent.planner import Selection, build_problem, pick_robot
from lpagent.validator import MAX_STOPS


class SelectionStrategy(Protocol):
    name: str

    def order(self, ctx: Context, robot: Robot) -> list[Stop]:
        """Devuelve los candidatos en el orden en que se intentarán agregar."""
        ...


def _manhattan(ctx: Context, s: Stop) -> int:
    return abs(s.x - ctx.origin[0]) + abs(s.y - ctx.origin[1])


class PriorityFirst:
    name = "priority_first"

    def order(self, ctx, robot):
        return sorted(ctx.orders, key=lambda s: (-s.priority, s.code))


class ClosestFirst:
    """Maximiza cuántos pedidos caben: los cercanos consumen menos batería."""
    name = "closest_first"

    def order(self, ctx, robot):
        return sorted(ctx.orders, key=lambda s: (_manhattan(ctx, s), s.code))


class ValueDensity:
    """Prioridad por unidad de distancia (heurística de la mochila): equilibra urgencia y costo."""
    name = "value_density"

    def order(self, ctx, robot):
        return sorted(ctx.orders, key=lambda s: (-(s.priority / (1 + _manhattan(ctx, s))), s.code))


STRATEGIES = {c.name: c for c in (PriorityFirst, ClosestFirst, ValueDensity)}


def strategy_by_name(name: str) -> SelectionStrategy:
    try:
        return STRATEGIES[name]()
    except KeyError:
        raise ValueError(f"estrategia desconocida: {name!r}; opciones: {sorted(STRATEGIES)}") from None


class PolicyPlanner:
    """Contexto del patrón. La estrategia es reemplazable (set_strategy) sin tocar al agente ni al solver."""

    def __init__(self, solver, strategy: SelectionStrategy | None = None, time_limit_s: float = 2.0):
        self.solver, self.strategy, self.time_limit_s = solver, strategy or PriorityFirst(), time_limit_s

    def set_strategy(self, strategy: SelectionStrategy) -> None:
        self.strategy = strategy

    def select(self, ctx: Context) -> Selection | None:
        robot = pick_robot(ctx)
        if robot is None or not ctx.orders:
            return None
        chosen: list[Stop] = []
        for cand in self.strategy.order(ctx, robot):
            if len(chosen) >= MAX_STOPS:
                break
            try:
                problem = build_problem(ctx, robot, chosen + [cand])
            except ValueError:
                continue
            if self.solver.solve(problem, self.time_limit_s).feasible:
                chosen.append(cand)
        if not chosen:
            return None
        return Selection(robot, chosen, f"{len(chosen)} pedidos con política {self.strategy.name} en {robot.code}", "rule")
