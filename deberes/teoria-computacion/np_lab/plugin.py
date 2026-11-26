"""Adaptador del deber de Teoría para el agente: LP_SOLVER_PLUGIN=np_lab.plugin:build

POLÍTICA DE SELECCIÓN (derivada de `python -m np_lab.bench`, ver docs/RESULTADOS_BENCHMARK.md):
  n <= 8  -> fuerza bruta (exacta; 0,04 s a n=8, 0,4 s a n=9, 4,4 s a n=10, >10 s a n=11).
  n <= 15 -> Held-Karp (exacta; 0,4 s a n=15 y ~1 s a n=16, memoria O(n·2^n) aún modesta).
  n  > 15 -> vecino más cercano + 2-opt (heurística: un «no» NO prueba que no exista un ciclo; `proven=False`).
Un tope duro de 12 paradas lo impone el validador del agente (MAX_STOPS), así que la rama heurística es de reserva."""
from __future__ import annotations

from . import tsp

EXACT_BRUTE_MAX_N = 8
EXACT_DP_MAX_N = 15


class NPSolver:
    name = "np_lab"

    def solve(self, problem, time_limit_s: float = 2.0):
        from lpagent.models import Solution  # import perezoso: np_lab no depende del agente

        n, dist, budget = problem.n, problem.dist, problem.budget
        if n == 0:
            return Solution(True, [], 0, "trivial", True)
        try:
            if n <= EXACT_BRUTE_MAX_N:
                tour, cost = tsp.brute_force(dist)
                algo, proven = "brute_force", True
            elif n <= EXACT_DP_MAX_N:
                tour, cost = tsp.held_karp(dist)
                algo, proven = "held_karp", True
            else:
                tour = tsp.two_opt(dist, tsp.nearest_neighbor(dist))
                cost, algo, proven = tsp.tour_cost(dist, tour), "nn+2opt", False
        except NotImplementedError:
            tour = tsp.nearest_neighbor(dist)             # reserva defensiva
            cost, algo, proven = tsp.tour_cost(dist, tour), "nearest_neighbor", False
        ok = cost <= budget and tsp.verify_tour(dist, budget, tour)
        note = "" if ok else ("el óptimo excede el presupuesto" if proven else "la heurística no halló un ciclo dentro del presupuesto (no prueba que no exista)")
        return Solution(ok, tour if ok else None, cost if ok else None, algo, proven, note)


def build():
    return NPSolver()
