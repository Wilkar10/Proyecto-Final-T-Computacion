import random

import pytest

from np_lab import logistica as L
from np_lab.instances import random_tsp
from np_lab.tsp import held_karp, tour_cost


def rnd(seed, n, hi=30):
    r = random.Random(seed)
    return [r.randint(1, hi) for _ in range(n)], [r.randint(1, 9) for _ in range(n)]


@pytest.mark.parametrize("seed", range(8))
def test_mochila_dp_igual_a_fuerza_bruta_y_voraz_no_mejora(seed):
    w, v = rnd(seed, 11)
    cap = sum(w) // 3
    bf, dp, gr = L.knapsack_bruteforce(w, v, cap), L.knapsack_dp(w, v, cap), L.knapsack_greedy(w, v, cap)
    assert bf[0] == dp[0] and L.verify_knapsack(w, cap, dp[1]) and L.verify_knapsack(w, cap, gr[1])
    assert gr[0] <= dp[0]


def test_verificador_de_mochila_rechaza_exceso_y_repetidos():
    assert not L.verify_knapsack([5, 5], 9, [0, 1])
    assert not L.verify_knapsack([5, 5], 20, [0, 0])


@pytest.mark.parametrize("seed", range(8))
def test_empaque_ffd_respeta_su_cota_y_el_exacto_es_valido(seed):
    w, _ = rnd(seed, 10, hi=9)
    cap = 10
    ffd, ex = L.first_fit_decreasing(w, cap), L.bin_packing_exact(w, cap)
    assert L.verify_bins(w, cap, ffd) and L.verify_bins(w, cap, ex)
    assert len(ex) <= len(ffd) <= 11 / 9 * len(ex) + 6 / 9 + 1e-9


def test_empaque_pieza_que_no_cabe_y_limite_exacto():
    with pytest.raises(ValueError):
        L.first_fit_decreasing([11], 10)
    with pytest.raises(ValueError):
        L.bin_packing_exact([1] * 20, 10)


def test_cobertura_exacta_valida_y_voraz_cubre():
    sets = {"A": {1, 2, 3}, "B": {3, 4}, "C": {4, 5, 6}, "D": {1, 4, 5}, "E": {2, 6}}
    u = {1, 2, 3, 4, 5, 6}
    ex, gr = L.set_cover_exact(u, sets), L.set_cover_greedy(u, sets)
    assert L.verify_set_cover(u, sets, ex) and L.verify_set_cover(u, sets, gr) and len(ex) <= len(gr)
    with pytest.raises(ValueError):
        L.set_cover_exact({1, 99}, {"A": {1}})


@pytest.mark.parametrize("seed", range(5))
def test_asignacion_exacta_valida_y_mejor_o_igual_que_voraz(seed):
    d = random_tsp(6, seed)
    budgets = [60, 60]
    ex, gr = L.assign_exact(d, budgets), L.assign_greedy(d, budgets)
    assert ex is not None and L.verify_assignment(d, ex[0], budgets)
    if gr:
        assert L.verify_assignment(d, gr[0], budgets) and ex[1] <= gr[1]


def test_asignacion_inviable_y_limite():
    d = random_tsp(4, 1)
    assert L.assign_exact(d, [1, 1]) is None and L.assign_greedy(d, [1, 1]) is None
    with pytest.raises(ValueError):
        L.assign_exact(random_tsp(10, 1), [50, 50])


def test_un_solo_robot_equivale_a_tsp():
    d = random_tsp(6, 3)
    ex = L.assign_exact(d, [10**6])
    assert ex[1] == held_karp(d)[1]


def test_plazos_distancia_minima_no_es_cumplir_el_sla():
    """Instancia hallada por búsqueda (semilla 3): TODOS los recorridos de costo mínimo violan algún plazo,
    pero existe uno factible más caro. Minimizar distancia no es cumplir el SLA."""
    from itertools import permutations
    d = random_tsp(5, 3)
    r = random.Random(3)
    dl = [r.randint(10, 40) for _ in range(5)]
    todos = [(tour_cost(d, [s + 1 for s in p]), p) for p in permutations(range(5))]
    c = min(t[0] for t in todos)
    assert all(not L.verify_deadlines(d, list(p), dl) for cost, p in todos if cost == c)
    best = L.best_with_deadlines(d, dl)
    assert best is not None and L.verify_deadlines(d, best[0], dl) and best[1] > c


@pytest.mark.parametrize("seed", range(6))
def test_plazos_dp_es_optimo_entre_los_factibles(seed):
    from itertools import permutations
    d = random_tsp(6, seed)
    r = random.Random(seed)
    dl = [r.randint(8, 40) for _ in range(6)]
    best = L.best_with_deadlines(d, dl)
    feas = [(tour_cost(d, [s + 1 for s in p]), p) for p in permutations(range(6)) if L.verify_deadlines(d, list(p), dl)]
    if not feas:
        assert best is None
    else:
        assert best is not None and best[1] == min(feas)[0] and L.verify_deadlines(d, best[0], dl)


def test_plazos_imposibles():
    d = random_tsp(4, 1)
    assert L.best_with_deadlines(d, [0, 0, 0, 0]) is None
