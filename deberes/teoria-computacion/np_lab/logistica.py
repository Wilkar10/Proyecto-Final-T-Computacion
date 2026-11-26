"""Problemas de decisión logística vistos desde la teoría de la computación.

Cada problema trae: (1) su VERIFICADOR (certificado → sí/no en tiempo polinomial: esto lo hace NP),
(2) un algoritmo EXACTO (exponencial o pseudo-polinomial) y (3) una HEURÍSTICA con su garantía (o ausencia de ella).
Mochila · empaque · cobertura · asignación a varios robots · recorrido con plazos."""
from __future__ import annotations

from itertools import combinations, product

from .tsp import held_karp, nearest_neighbor, two_opt


# ===================================================================== MOCHILA 0/1 (¿qué pedidos suben al viaje?)
def verify_knapsack(weights, cap, chosen) -> bool:
    return len(set(chosen)) == len(chosen) and all(0 <= i < len(weights) for i in chosen) and sum(weights[i] for i in chosen) <= cap


def knapsack_bruteforce(weights, values, cap):
    n, best = len(weights), (0.0, ())
    for mask in range(1 << n):
        idx = [i for i in range(n) if (mask >> i) & 1]
        if sum(weights[i] for i in idx) <= cap:
            v = sum(values[i] for i in idx)
            if v > best[0]:
                best = (v, tuple(idx))
    return best


def knapsack_dp(weights, values, cap):
    """Pseudo-polinomial O(n·cap): polinomial en el VALOR numérico de cap, no en su tamaño en bits.
    Pesos enteros (use gramos o kg redondeados)."""
    n = len(weights)
    best = [[0.0] * (cap + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        w, v = weights[i - 1], values[i - 1]
        for c in range(cap + 1):
            best[i][c] = best[i - 1][c]
            if w <= c and best[i - 1][c - w] + v > best[i][c]:
                best[i][c] = best[i - 1][c - w] + v
    chosen, c = [], cap
    for i in range(n, 0, -1):
        if best[i][c] != best[i - 1][c]:
            chosen.append(i - 1)
            c -= weights[i - 1]
    return best[n][cap], tuple(sorted(chosen))


def knapsack_greedy(weights, values, cap):
    """Por densidad valor/peso. Sin garantía de factor constante por sí sola (hay que comparar con el mejor ítem solo)."""
    order = sorted(range(len(weights)), key=lambda i: -values[i] / weights[i])
    used, chosen = 0, []
    for i in order:
        if used + weights[i] <= cap:
            used += weights[i]
            chosen.append(i)
    return sum(values[i] for i in chosen), tuple(sorted(chosen))


# ===================================================================== EMPAQUE (¿cuántos viajes hacen falta?)
def verify_bins(weights, cap, bins) -> bool:
    flat = sorted(i for b in bins for i in b)
    return flat == list(range(len(weights))) and all(sum(weights[i] for i in b) <= cap for b in bins)


def first_fit_decreasing(weights, cap):
    """Heurística: FFD(I) ≤ 11/9·OPT(I) + 6/9 (Johnson, 1973). Exige que cada pieza quepa sola."""
    if any(w > cap for w in weights):
        raise ValueError("hay un pedido que no cabe en un solo viaje")
    bins: list[list[int]] = []
    loads: list[float] = []
    for i in sorted(range(len(weights)), key=lambda i: -weights[i]):
        for b, load in enumerate(loads):
            if load + weights[i] <= cap:
                bins[b].append(i)
                loads[b] += weights[i]
                break
        else:
            bins.append([i])
            loads.append(weights[i])
    return bins


def bin_packing_exact(weights, cap, max_n: int = 14):
    """Mínimo de viajes por búsqueda con retroceso. Exponencial: se limita a max_n piezas."""
    n = len(weights)
    if n > max_n:
        raise ValueError(f"exacto solo hasta {max_n} pedidos (NP-difícil)")
    best = [first_fit_decreasing(weights, cap)]
    order = sorted(range(n), key=lambda i: -weights[i])

    def go(k, bins, loads):
        if len(bins) >= len(best[0]):
            return
        if k == n:
            best[0] = [list(b) for b in bins]
            return
        i = order[k]
        for b in range(len(bins)):
            if loads[b] + weights[i] <= cap:
                bins[b].append(i); loads[b] += weights[i]
                go(k + 1, bins, loads)
                bins[b].pop(); loads[b] -= weights[i]
        bins.append([i]); loads.append(weights[i])
        go(k + 1, bins, loads)
        bins.pop(); loads.pop()

    go(0, [], [])
    return best[0]


# ===================================================================== COBERTURA (¿qué depósitos mantener?)
def verify_set_cover(universe, sets: dict, chosen) -> bool:
    covered = set()
    for name in chosen:
        covered |= sets[name]
    return set(universe) <= covered


def set_cover_greedy(universe, sets: dict):
    """Elige siempre el conjunto que cubre más elementos nuevos: aproximación H(n) ≈ ln n + 1 (y no se puede mejorar
    sustancialmente en tiempo polinomial salvo que P = NP)."""
    left, chosen = set(universe), []
    while left:
        name = max(sets, key=lambda s: len(sets[s] & left))
        if not sets[name] & left:
            raise ValueError("el universo no se puede cubrir con estos conjuntos")
        chosen.append(name)
        left -= sets[name]
    return chosen


def set_cover_exact(universe, sets: dict):
    names = list(sets)
    for k in range(1, len(names) + 1):
        for combo in combinations(names, k):
            if verify_set_cover(universe, sets, combo):
                return list(combo)
    raise ValueError("el universo no se puede cubrir con estos conjuntos")


# ===================================================================== ASIGNACIÓN A VARIOS ROBOTS
def _sub(dist, nodes):
    idx = [0] + [i + 1 for i in nodes]
    return [[dist[a][b] for b in idx] for a in idx]


def route_cost(dist, nodes) -> tuple[list[int], int]:
    """Mejor ciclo para el grupo `nodes` (índices de paradas 0..n-1): Held-Karp si ≤ 12, si no NN+2-opt."""
    if not nodes:
        return [], 0
    d = _sub(dist, nodes)
    if len(nodes) <= 12:
        tour, c = held_karp(d)
    else:
        tour = two_opt(d, nearest_neighbor(d))
        c = sum(d[a][b] for a, b in zip([0, *tour], [*tour, 0]))
    return [nodes[t - 1] for t in tour], c


def verify_assignment(dist, routes, budgets) -> bool:
    n = len(dist) - 1
    flat = sorted(s for r in routes for s in r)
    if flat != list(range(n)) or len(routes) > len(budgets):
        return False
    for r, b in zip(routes, budgets):
        path = [0, *[s + 1 for s in r], 0]
        if sum(dist[a][c] for a, c in zip(path, path[1:])) > b:
            return False
    return True


def assign_exact(dist, budgets, max_n: int = 9):
    """Enumera k^n asignaciones; para cada grupo resuelve su TSP. Devuelve (rutas, costo_total) o None si es inviable."""
    n, k = len(dist) - 1, len(budgets)
    if n > max_n:
        raise ValueError(f"exacto solo hasta {max_n} paradas: k^n crece demasiado")
    cache: dict = {}
    best = None
    for labels in product(range(k), repeat=n):
        groups = [tuple(i for i in range(n) if labels[i] == r) for r in range(k)]
        total, routes, ok = 0, [], True
        for r, g in enumerate(groups):
            if g not in cache:
                cache[g] = route_cost(dist, list(g))
            tour, c = cache[g]
            if c > budgets[r]:
                ok = False
                break
            total += c
            routes.append(tour)
        if ok and (best is None or total < best[1]):
            best = (routes, total)
    return best


def assign_greedy(dist, budgets):
    """Inserción más barata, parada por parada. Rápido y sin garantía; puede declarar inviable algo que sí lo es."""
    n, k = len(dist) - 1, len(budgets)
    routes: list[list[int]] = [[] for _ in range(k)]
    costs = [0] * k
    for s in sorted(range(n), key=lambda s: dist[0][s + 1]):
        options = []
        for r in range(k):
            tour, c = route_cost(dist, routes[r] + [s])
            if c <= budgets[r]:
                options.append((c - costs[r], r, tour, c))
        if not options:
            return None
        _, r, tour, c = min(options)
        routes[r], costs[r] = tour, c
    return routes, sum(costs)


# ===================================================================== RECORRIDO CON PLAZOS (SLA)
def arrival_times(dist, tour, speed_min_per_cost: float = 1.0):
    t, prev, out = 0.0, 0, []
    for s in tour:
        t += dist[prev][s + 1] * speed_min_per_cost
        out.append(t)
        prev = s + 1
    return out


def verify_deadlines(dist, tour, deadlines, speed_min_per_cost: float = 1.0) -> bool:
    if sorted(tour) != list(range(len(dist) - 1)):
        return False
    return all(a <= deadlines[s] for a, s in zip(arrival_times(dist, tour, speed_min_per_cost), tour))


def earliest_deadline_first(dist, deadlines):
    return sorted(range(len(dist) - 1), key=lambda s: deadlines[s])


def best_with_deadlines(dist, deadlines, speed_min_per_cost: float = 1.0):
    """Entre los recorridos que cumplen TODOS los plazos, el de menor costo. DP sobre subconjuntos O(n²·2ⁿ):
    sin esperas, llegar antes a (S, j) domina a llegar después. Devuelve (tour, costo_ciclo) o None."""
    n = len(dist) - 1
    INF = float("inf")
    dp = [[INF] * n for _ in range(1 << n)]
    par = [[-1] * n for _ in range(1 << n)]
    for j in range(n):
        t = dist[0][j + 1] * speed_min_per_cost
        if t <= deadlines[j]:
            dp[1 << j][j] = dist[0][j + 1]
    for mask in range(1, 1 << n):
        for j in range(n):
            c = dp[mask][j]
            if (mask >> j) & 1 and c < INF:
                for k in range(n):
                    if not (mask >> k) & 1:
                        nc = c + dist[j + 1][k + 1]
                        if nc * speed_min_per_cost <= deadlines[k] and nc < dp[mask | (1 << k)][k]:
                            dp[mask | (1 << k)][k], par[mask | (1 << k)][k] = nc, j
    full = (1 << n) - 1
    cand = [(dp[full][j] + dist[j + 1][0], j) for j in range(n) if dp[full][j] < INF]
    if not cand:
        return None
    best, last = min(cand)
    tour, mask = [], full
    while last != -1:
        tour.append(last)
        prev = par[mask][last]
        mask ^= 1 << last
        last = prev
    return tour[::-1], best
