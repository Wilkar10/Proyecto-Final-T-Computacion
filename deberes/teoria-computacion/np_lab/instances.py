"""Generadores de instancias reproducibles (semilla fija)."""
from __future__ import annotations

import random


def random_tsp(n: int, seed: int = 1, width: int = 12, height: int = 8) -> list[list[int]]:
    """Matriz de distancias (n+1)x(n+1) entre un origen en (0,0) y n puntos al azar. Distancia Manhattan:
    simplificación del plano real (el agente usa costos de Dijkstra sobre la grilla del almacén)."""
    rng = random.Random(seed)
    pts = [(0, 0)] + [(rng.randrange(width), rng.randrange(height)) for _ in range(n)]
    return [[abs(ax - bx) + abs(ay - by) for (bx, by) in pts] for (ax, ay) in pts]


def random_3sat(n_vars: int, n_clauses: int, seed: int = 1) -> list[tuple[int, int, int]]:
    """Cláusulas 3-CNF; literal +i / -i (variables 1..n). Cerca de m/n ≈ 4.27 está el umbral difícil."""
    rng = random.Random(seed)
    out = []
    for _ in range(n_clauses):
        vs = rng.sample(range(1, n_vars + 1), 3)
        out.append(tuple(v if rng.random() < 0.5 else -v for v in vs))
    return out


def random_graph(n: int, p: float, seed: int = 1) -> list[tuple[int, int]]:
    rng = random.Random(seed)
    return [(i, j) for i in range(n) for j in range(i + 1, n) if rng.random() < p]
