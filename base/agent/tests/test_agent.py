import json

import pytest

from lpagent.agent import DispatchAgent
from lpagent.audit import Audit, MemorySink
from lpagent.baseline import BaselineSolver, DryRunActuator, FixtureData
from lpagent.grid import DEFAULT_LAYOUT, dijkstra, distance_matrix
from lpagent.models import Context, Proposal, Robot, Solution, Stop, TripProblem
from lpagent.planner import LLMPlanner, RulePlanner, build_problem
from lpagent.validator import MAX_STOPS, verify_certificate, verify_proposal


# ---------------------------------------------------------------- grilla (mismos valores que AStarPathfinderTest.java)
def test_grid_matches_java_tests():
    d = dijkstra(DEFAULT_LAYOUT, (0, 0))
    assert d[(11, 0)] == 11
    assert (1, 1) not in d  # estantería
    assert dijkstra(DEFAULT_LAYOUT, (3, 3))[(7, 3)] == 6  # rodea la zona congestionada (directo costaría 16)


def test_unreachable_destination_raises():
    with pytest.raises(ValueError):
        distance_matrix(DEFAULT_LAYOUT, [(0, 0), (1, 1)])


# ---------------------------------------------------------------- solver base + validador
def square_problem(budget):
    # origen (0,0), paradas en las esquinas de un rectángulo de pasillos libres
    ctx = FixtureData().load_context()
    stops = [Stop("A", 11, 0), Stop("B", 11, 2), Stop("C", 0, 2)]
    return TripProblem(stops, distance_matrix(ctx.grid_rows, [(0, 0)] + [(s.x, s.y) for s in stops]), budget)


def test_bruteforce_is_exact_and_certificate_checks():
    p = square_problem(budget=100)
    sol = BaselineSolver().solve(p, 2)
    assert sol.feasible and sol.proven and sol.algorithm == "brute_force"
    assert verify_certificate(p, sol.tour)[0]
    assert sol.cost == p.tour_cost(sol.tour) == 26  # 0,0 -> C -> B -> A -> 0,0 recorre el perímetro (11+11+2+2)


def test_infeasible_is_proven_by_exact_solver():
    sol = BaselineSolver().solve(square_problem(budget=10), 2)
    assert not sol.feasible and sol.proven


def test_certificate_rejects_bad_tours():
    p = square_problem(100)
    assert not verify_certificate(p, [1, 2])[0]          # falta una parada
    assert not verify_certificate(p, [1, 1, 2])[0]       # repetida
    assert not verify_certificate(square_problem(5), [1, 2, 3])[0]  # excede presupuesto


def test_validator_business_rules():
    p = square_problem(100)
    ok, errs = verify_proposal(p, [3, 2, 1], Robot("R", 0, 0, 100), ["A", "B", "C"])
    assert ok, errs
    assert not verify_proposal(p, [3, 2, 1], Robot("R", 0, 0, 100, "BUSY"), ["A", "B", "C"])[0]
    assert not verify_proposal(p, [3, 2, 1], Robot("R", 0, 0, 40), ["A", "B", "C"])[0]  # 40-26 < reserva 20
    assert not verify_proposal(p, [3, 2, 1], Robot("R", 0, 0, 100), ["A", "A", "C"])[0]


# ---------------------------------------------------------------- agente de punta a punta (nivel 1: sugiere)
class SpyActuator(DryRunActuator):
    def __init__(self):
        self.calls = 0

    def execute(self, proposal):
        self.calls += 1
        return super().execute(proposal)


def make_agent(planner=None, solver=None, actuator=None):
    sink = MemorySink()
    agent = DispatchAgent(FixtureData(), solver or BaselineSolver(), actuator or SpyActuator(), Audit(sink), planner)
    return agent, sink


def test_plan_creates_pending_proposal_and_never_executes():
    spy = SpyActuator()
    agent, sink = make_agent(actuator=spy)
    p, why = agent.plan()
    assert p and why == "ok" and p.status == "PENDING_APPROVAL"
    assert spy.calls == 0                                  # autonomía nivel 1: planificar no actúa
    assert p.robot == "AMR-01"                             # el de más batería
    assert p.cost <= p.budget == 80                        # 100 - reserva 20
    kinds = [e["kind"] for e in sink.events]
    assert kinds[0] == "plan_started" and "solver_result" in kinds and "validation" in kinds and kinds[-1] == "proposal_created"


def test_high_priority_orders_are_preferred():
    agent, _ = make_agent()
    p, _ = agent.plan()
    assert "LP-DEMO01" in p.order_codes and "LP-DEMO05" in p.order_codes  # prioridad 3.0


def test_approval_requires_identified_human():
    spy = SpyActuator()
    agent, _ = make_agent(actuator=spy)
    p, _ = agent.plan()
    with pytest.raises(PermissionError):
        agent.decide(p.proposal_id, "  ", True)
    assert spy.calls == 0
    done = agent.decide(p.proposal_id, "maria.compras", True)
    assert done.status == "EXECUTED" and done.decided_by == "maria.compras" and spy.calls == 1
    with pytest.raises(ValueError):
        agent.decide(p.proposal_id, "maria.compras", True)  # no se aprueba dos veces


def test_reject_does_not_execute():
    spy = SpyActuator()
    agent, _ = make_agent(actuator=spy)
    p, _ = agent.plan()
    assert agent.decide(p.proposal_id, "ana", False).status == "REJECTED" and spy.calls == 0


def test_actuator_failure_is_recorded_not_raised():
    class Boom:
        def execute(self, proposal):
            raise RuntimeError("lab caído")

    agent, _ = make_agent(actuator=Boom())
    p, _ = agent.plan()
    assert agent.decide(p.proposal_id, "ana", True).status == "FAILED"


def test_no_robot_available_returns_reason():
    class NoRobots(FixtureData):
        def load_context(self):
            c = super().load_context()
            return Context(c.grid_rows, [Robot("X", 0, 0, 15)], c.orders, c.origin)

    agent = DispatchAgent(NoRobots(), BaselineSolver(), SpyActuator(), Audit(MemorySink()))
    p, why = agent.plan()
    assert p is None and why


# ---------------------------------------------------------------- planificador LLM con cliente FALSO (sin red)
class ScriptedClient:
    """Reproduce respuestas del 'modelo' en orden; registra lo que recibe."""

    def __init__(self, script):
        self.script, self.seen = list(script), []

    def complete(self, system, messages, tools):
        self.seen.append(json.loads(json.dumps(messages, default=str)))
        return self.script.pop(0)


def tool(i, name, **inp):
    return [{"type": "tool_use", "id": f"t{i}", "name": name, "input": inp}]


def test_llm_planner_happy_path_still_goes_through_solver_and_validator():
    client = ScriptedClient([
        tool(1, "list_orders"),
        tool(2, "check_trip", robot_code="AMR-01", order_codes=["LP-DEMO01", "LP-DEMO05"]),
        tool(3, "propose_trip", robot_code="AMR-01", order_codes=["LP-DEMO01", "LP-DEMO05"], rationale="prioridad alta"),
    ])
    agent, sink = make_agent(planner=LLMPlanner(client, BaselineSolver()))
    p, _ = agent.plan()
    assert p and p.source == "llm" and sorted(p.order_codes) == ["LP-DEMO01", "LP-DEMO05"]
    assert p.algorithm == "brute_force"  # el recorrido lo calculó el solver, no el modelo


def test_llm_hallucinated_codes_are_rejected_and_fallback_used():
    client = ScriptedClient([
        tool(1, "propose_trip", robot_code="AMR-99", order_codes=["LP-FAKE"], rationale="inventado"),
        tool(2, "propose_trip", robot_code="AMR-01", order_codes=["LP-NOPE"], rationale="inventado"),
        [{"type": "text", "text": "no sé"}],
    ])
    agent, sink = make_agent(planner=LLMPlanner(client, BaselineSolver(), max_steps=4))
    p, _ = agent.plan()
    assert p and p.source == "fallback"
    assert "fallback_used" in [e["kind"] for e in sink.events]


def test_llm_infeasible_selection_is_blocked_by_validator():
    class LowBattery(FixtureData):
        def load_context(self):
            c = super().load_context()
            return Context(c.grid_rows, [Robot("AMR-01", 0, 0, 45)], c.orders, c.origin)  # presupuesto 25

    everything = ["LP-DEMO01", "LP-DEMO02", "LP-DEMO03", "LP-DEMO04", "LP-DEMO05"]
    client = ScriptedClient([tool(1, "propose_trip", robot_code="AMR-01", order_codes=everything, rationale="todo")])
    sink = MemorySink()
    agent = DispatchAgent(LowBattery(), BaselineSolver(), SpyActuator(), Audit(sink), LLMPlanner(client, BaselineSolver()))
    p, _ = agent.plan()
    assert p is not None and p.source == "fallback" and p.cost <= p.budget == 25
    assert len(p.order_codes) < 5                      # el modelo pidió demasiado; el solver exacto lo rechazó
    assert "fallback_used" in [e["kind"] for e in sink.events]


def test_llm_step_limit():
    client = ScriptedClient([tool(i, "list_orders") for i in range(10)])
    sel = LLMPlanner(client, BaselineSolver(), max_steps=3).select(FixtureData().load_context())
    assert sel is None and len(client.script) == 7  # solo consumió 3 pasos


def test_broken_planner_does_not_crash_agent():
    class Broken:
        def select(self, ctx):
            raise RuntimeError("falló")

    agent, sink = make_agent(planner=Broken())
    p, _ = agent.plan()
    assert p and p.source == "fallback"
    assert "planner_error" in [e["kind"] for e in sink.events]


def test_stop_cap_constant():
    assert MAX_STOPS == 12
