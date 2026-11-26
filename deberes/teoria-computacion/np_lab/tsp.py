"""Recorrido (TSP, versión de decisión): ¿existe un ciclo desde el origen 0 que visite 1..n con costo <= budget?
dist es una matriz (n+1)x(n+1). Un 'tour' es una permutación de 1..n."""
from __future__ import annotations

import itertools


def tour_cost(dist: list[list[int]], tour: list[int]) -> int:
    path = [0, *tour, 0]
    return sum(dist[a][b] for a, b in zip(path, path[1:]))


# ------------------------------------------------------------------------- VERIFICADOR (dado)
def verify_tour(dist, budget: int, tour: list[int]) -> bool:
    """V(x, certificado): O(n). Es la prueba de que TSP-decisión está en NP."""
    n = len(dist) - 1
    return sorted(tour) == list(range(1, n + 1)) and tour_cost(dist, tour) <= budget


# ------------------------------------------------------------------------- ALGORITMOS DADOS
def brute_force(dist, budget: int | None = None):
    """Exacto, O(n!·n). Devuelve (mejor_tour, costo). Si budget no es None, corta al hallar uno que cabe."""
    n = len(dist) - 1
    best, best_c = None, None
    for perm in itertools.permutations(range(1, n + 1)):
        c = tour_cost(dist, list(perm))
        if best_c is None or c < best_c:
            best, best_c = list(perm), c
            if budget is not None and c <= budget:
                break
    return best, best_c


def nearest_neighbor(dist) -> list[int]:
    """Heurística O(n²). Sin garantía de aproximación en general."""
    n = len(dist) - 1
    left, cur, order = set(range(1, n + 1)), 0, []
    while left:
        nxt = min(left, key=lambda j: (dist[cur][j], j))
        order.append(nxt)
        left.remove(nxt)
        cur = nxt
    return order


# ------------------------------------------------------------------------- ALGORITMOS IMPLEMENTADOS
def held_karp(dist) -> tuple[list[int], int]:
    """Programación dinámica sobre subconjuntos: O(n²·2ⁿ) tiempo, O(n·2ⁿ) espacio.
    Debe devolver (tour_óptimo, costo_óptimo) y reconstruir el tour. Para n == 0 devuelve ([], 0)."""
    n = len(dist) - 1
    if n == 0:
        return [], 0
    INF = float("inf")
    full = (1 << n) - 1
    dp = [[INF] * n for _ in range(1 << n)]       # dp[S][j]: costo mínimo de salir de 0, visitar S y terminar en j
    par = [[-1] * n for _ in range(1 << n)]
    for j in range(n):
        dp[1 << j][j] = dist[0][j + 1]
    for mask in range(1, 1 << n):
        for j in range(n):
            if not (mask >> j) & 1 or dp[mask][j] == INF:
                continue
            for k in range(n):
                if (mask >> k) & 1:
                    continue
                nm, c = mask | (1 << k), dp[mask][j] + dist[j + 1][k + 1]
                if c < dp[nm][k]:
                    dp[nm][k], par[nm][k] = c, j
    best, last = min((dp[full][j] + dist[j + 1][0], j) for j in range(n))
    tour, mask = [], full
    while last != -1:                              # reconstrucción hacia atrás
        tour.append(last + 1)
        prev = par[mask][last]
        mask ^= 1 << last
        last = prev
    return tour[::-1], int(best)


def two_opt(dist, tour: list[int], max_passes: int = 50) -> list[int]:
    """Mejora local 2-opt (invertir segmentos del tour mientras reduzca el costo).
    Debe devolver una permutación válida de 1..n con costo <= el del tour recibido."""
    t = list(tour)
    best = tour_cost(dist, t)
    for _ in range(max_passes):
        improved = False
        for i in range(len(t) - 1):
            for j in range(i + 1, len(t)):
                cand = t[:i] + t[i:j + 1][::-1] + t[j + 1:]
                c = tour_cost(dist, cand)
                if c < best:
                    t, best, improved = cand, c, True
        if not improved:
            break
    return t
