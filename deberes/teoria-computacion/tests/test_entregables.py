"""Pruebas de los entregables del deber (verdes: el sistema ya está implementado). Ejecutar: pytest -v"""
import pytest

from np_lab import sat, tsp, vertex_cover
from np_lab.instances import random_3sat, random_graph, random_tsp



@pytest.mark.parametrize("seed", range(20))
@pytest.mark.parametrize("n", [1, 3, 6, 8])
def test_held_karp_matches_bruteforce(n, seed):
    d = random_tsp(n, seed)
    tour, cost = tsp.held_karp(d)
    assert tsp.tour_cost(d, tour) == cost == tsp.brute_force(d)[1]


def test_held_karp_empty_instance():
    assert tsp.held_karp([[0]]) == ([], 0)


def test_held_karp_scales_beyond_bruteforce():
    d = random_tsp(12, 5)  # 12! ≈ 479 millones de permutaciones: inviable por fuerza bruta
    tour, cost = tsp.held_karp(d)
    assert sorted(tour) == list(range(1, 13)) and tsp.tour_cost(d, tour) == cost


@pytest.mark.parametrize("seed", range(10))
def test_two_opt_never_worsens_and_stays_valid(seed):
    d = random_tsp(10, seed)
    start = tsp.nearest_neighbor(d)
    out = tsp.two_opt(d, start)
    assert sorted(out) == list(range(1, 11))
    assert tsp.tour_cost(d, out) <= tsp.tour_cost(d, start)


def test_two_opt_improves_a_bad_tour():
    d = random_tsp(9, 2)
    bad = list(range(9, 0, -1))
    assert tsp.tour_cost(d, tsp.two_opt(d, bad)) < tsp.tour_cost(d, bad)


@pytest.mark.parametrize("seed", range(25))
def test_dpll_agrees_with_bruteforce_near_threshold(seed):
    n = 10
    cl = random_3sat(n, 43, seed)  # m/n = 4.3: zona difícil, mezcla de SAT e UNSAT
    expected = sat.brute_force(cl, n)
    got = sat.dpll(cl, n)
    assert (got is None) == (expected is None)
    if got is not None:
        assert set(got) == set(range(1, n + 1)) and sat.verify_sat(cl, got)


def test_dpll_trivial_cases():
    assert sat.dpll([], 3) is not None
    assert sat.dpll([(1,), (-1,)], 1) is None
    assert sat.verify_sat([(1,), (2,)], sat.dpll([(1,), (2,)], 2))


@pytest.mark.parametrize("seed", range(20))
def test_vertex_cover_2_approximation(seed):
    n = 9
    edges = random_graph(n, 0.3, seed)
    cover = vertex_cover.approx_2(edges)
    assert vertex_cover.verify_cover(edges, len(cover), cover)
    opt = next(k for k in range(n + 1) if vertex_cover.brute_force(edges, n, k) is not None)
    assert len(cover) <= 2 * opt
