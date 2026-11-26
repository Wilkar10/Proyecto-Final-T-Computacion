"""Pruebas de la BASE entregada (verdes desde el inicio)."""
import itertools

from np_lab import sat, tsp, vertex_cover
from np_lab.instances import random_3sat, random_graph, random_tsp


def test_tsp_verifier_accepts_and_rejects():
    d = random_tsp(5, seed=3)
    tour, cost = tsp.brute_force(d)
    assert tsp.verify_tour(d, cost, tour)
    assert not tsp.verify_tour(d, cost - 1, tour)            # presupuesto más estricto que el óptimo
    assert not tsp.verify_tour(d, 10**6, tour[:-1])          # faltan paradas
    assert not tsp.verify_tour(d, 10**6, tour + [tour[0]])   # repetida


def test_brute_force_is_optimal_on_tiny_case():
    d = random_tsp(4, seed=7)
    best = min(tsp.tour_cost(d, list(p)) for p in itertools.permutations(range(1, 5)))
    assert tsp.brute_force(d)[1] == best


def test_nearest_neighbor_is_a_valid_tour_not_necessarily_optimal():
    d = random_tsp(8, seed=11)
    t = tsp.nearest_neighbor(d)
    assert sorted(t) == list(range(1, 9))
    assert tsp.tour_cost(d, t) >= tsp.brute_force(d)[1]


def test_sat_verifier_and_bruteforce():
    cl = [(1, 2, 3), (-1, -2, 3), (1, -3, 2)]
    a = sat.brute_force(cl, 3)
    assert a is not None and sat.verify_sat(cl, a)
    assert sat.brute_force([(1,), (-1,)], 1) is None


def test_vertex_cover_verifier_and_bruteforce():
    edges = [(0, 1), (1, 2), (2, 3)]
    c = vertex_cover.brute_force(edges, 4, 2)
    assert c is not None and vertex_cover.verify_cover(edges, 2, c)
    assert vertex_cover.brute_force(edges, 4, 1) is None


def test_generators_are_reproducible():
    assert random_tsp(6, 5) == random_tsp(6, 5)
    assert random_3sat(8, 20, 5) == random_3sat(8, 20, 5)
    assert random_graph(8, 0.3, 5) == random_graph(8, 0.3, 5)


def test_plugin_works_with_the_agent_even_before_the_tasks_are_done():
    """La base degrada con elegancia: sin Held-Karp/2-opt usa la brute force (n<=8) o NN, y el validador manda."""
    from lpagent.agent import DispatchAgent
    from lpagent.audit import Audit, MemorySink
    from lpagent.baseline import DryRunActuator, FixtureData
    from np_lab.plugin import build

    agent = DispatchAgent(FixtureData(), build(), DryRunActuator(), Audit(MemorySink()))
    p, why = agent.plan()
    assert p is not None, why
    assert p.cost <= p.budget
