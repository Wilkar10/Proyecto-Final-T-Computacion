import json

import pytest
from lpagent.audit import MemorySink
from lpagent.baseline import BaselineSolver, FixtureData
from lpagent.labclient import LabError
from lpagent.models import Context, Proposal, Robot, Stop

from lp_patterns import compose
from lp_patterns.adapter import LabOrderAdapter, ToolCallsLLMAdapter
from lp_patterns.command import ApproveCommand, CommandBus, NotUndoable, PlanCommand, RejectCommand
from lp_patterns.decorator import AuditedActuator, RetryingActuator
from lp_patterns.observer import EventBus, ObservableAudit
from lp_patterns.strategy import ClosestFirst, PolicyPlanner, PriorityFirst, ValueDensity, strategy_by_name
from lp_patterns.template import MarkdownRenderer, PlainRenderer, ProposalRenderer

GRID = ["............"] * 8


def ctx(orders, battery=100):
    return Context(GRID, [Robot("AMR-01", 0, 0, battery)], orders)


def proposal():
    return Proposal(proposal_id="p1", robot="AMR-01", order_codes=["A", "B"], cost=30, budget=80, battery_before=100,
                    algorithm="brute_force", exact=True, rationale="r")


# ------------------------------------------------------------------ Strategy
def test_strategies_order_candidates_differently():
    orders = [Stop("FAR-HI", 11, 7, 3), Stop("NEAR-LO", 1, 0, 1), Stop("MID", 4, 3, 2)]
    c = ctx(orders)
    assert [s.code for s in PriorityFirst().order(c, c.robots[0])][0] == "FAR-HI"
    assert [s.code for s in ClosestFirst().order(c, c.robots[0])][0] == "NEAR-LO"
    assert [s.code for s in ValueDensity().order(c, c.robots[0])][0] == "NEAR-LO"


def test_strategy_changes_the_outcome_when_battery_is_scarce():
    orders = [Stop("FAR-HI", 11, 7, 3), Stop("N1", 1, 0, 1), Stop("N2", 2, 0, 1), Stop("N3", 3, 0, 1)]
    c = ctx(orders, battery=50)             # presupuesto 30: el pedido lejano (ciclo >= 36) no cabe
    s = BaselineSolver()
    assert {x.code for x in PolicyPlanner(s, ClosestFirst()).select(c).stops} == {"N1", "N2", "N3"}
    p = PolicyPlanner(s, PriorityFirst())
    assert "FAR-HI" not in {x.code for x in p.select(c).stops}
    p.set_strategy(ClosestFirst())           # cambio en caliente
    assert p.strategy.name == "closest_first"


def test_unknown_strategy_is_explicit():
    with pytest.raises(ValueError, match="desconocida"):
        strategy_by_name("magia")


# ------------------------------------------------------------------ Observer
def test_observers_get_events_and_a_broken_one_does_not_break_the_agent():
    bus, seen = EventBus(), []
    bus.subscribe("a", seen.append)
    bus.subscribe("*", lambda e: 1 / 0)          # observador defectuoso
    bus.subscribe("*", lambda e: seen.append("star"))
    bus.publish({"kind": "a"})
    assert seen == [{"kind": "a"}, "star"] and len(bus.errors) == 1


def test_observable_audit_is_an_audit_and_publishes():
    bus, got, sink = EventBus(), [], MemorySink()
    bus.subscribe("x", got.append)
    ObservableAudit(bus, sink).log("x", v=1)
    assert got[0]["v"] == 1 and sink.events[0]["kind"] == "x"


# ------------------------------------------------------------------ Template Method
def test_template_fixes_the_skeleton_and_subclasses_fill_steps():
    md, plain = MarkdownRenderer().render(proposal()), PlainRenderer().render(proposal())
    assert md.startswith("## Propuesta p1") and md.rstrip().endswith("_") and "Costo" in md
    assert plain.splitlines()[0].startswith("[p1]") and len(plain.splitlines()) == 2    # sin pie (gancho vacío)


def test_template_method_is_abstract():
    with pytest.raises(TypeError):
        ProposalRenderer()


# ------------------------------------------------------------------ Decorator
class Flaky:
    def __init__(self, errors):
        self.errors, self.calls = list(errors), 0

    def execute(self, p):
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return {"ok": True}


def test_retry_only_transient_and_stops_at_limit():
    sleeps = []
    inner = Flaky([LabError(503, "x"), LabError(0, "net")])
    assert RetryingActuator(inner, sleep=sleeps.append).execute(proposal()) == {"ok": True} and inner.calls == 3 and len(sleeps) == 2
    permanent = Flaky([LabError(409, "conflicto")])
    with pytest.raises(LabError):
        RetryingActuator(permanent, sleep=lambda s: None).execute(proposal())
    assert permanent.calls == 1                  # 4xx: no se reintenta


def test_audited_actuator_records_failures():
    sink = MemorySink()
    from lpagent.audit import Audit
    a = AuditedActuator(Flaky([LabError(500, "boom")]), Audit(sink))
    with pytest.raises(LabError):
        a.execute(proposal())
    assert sink.events[0]["kind"] == "actuator_attempt" and sink.events[0]["ok"] is False


# ------------------------------------------------------------------ Adapter
def test_lab_order_adapter():
    s = LabOrderAdapter(lambda c: 3.0).to_stop({"code": "LP-1", "destX": "4", "destY": 2, "customer": "X"})
    assert s == Stop("LP-1", 4, 2, 3.0)


def test_llm_adapter_translates_both_directions():
    seen = {}

    def vendor(messages, tools):
        seen["messages"], seen["tools"] = messages, tools
        return {"message": {"content": "ok", "tool_calls": [{"id": "c1", "function": {"name": "list_orders", "arguments": "{}"}},
                                                           {"id": "c2", "function": {"name": "check_trip", "arguments": "{no json"}}]}}

    blocks = ToolCallsLLMAdapter(vendor).complete(
        "SYS", [{"role": "user", "content": "hola"},
                {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "list_robots", "input": {}}]},
                {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "{}"}]}],
        [{"name": "list_orders", "description": "d", "input_schema": {"type": "object"}}])
    assert [b["type"] for b in blocks] == ["text", "tool_use", "tool_use"] and blocks[2]["input"] == {}   # JSON corrupto tolerado
    assert seen["messages"][0] == {"role": "system", "content": "SYS"}
    assert seen["messages"][2]["tool_calls"][0]["function"]["name"] == "list_robots"
    assert seen["messages"][3] == {"role": "tool", "tool_call_id": "t1", "content": "{}"}
    assert seen["tools"][0]["function"]["parameters"] == {"type": "object"}


# ------------------------------------------------------------------ Command + integración de los 7
def test_full_flow_wires_every_pattern():
    w = compose.build(sinks=[MemorySink()], strategy="closest_first")
    p, why = w.commands.run(PlanCommand(w.agent))
    assert p is not None, why
    assert w.notifier.outbox and "Propuesta" in w.notifier.outbox[0]                     # Observer + Template
    done = w.commands.run(ApproveCommand(w.agent, p.proposal_id, "ana"))
    assert done.status == "EXECUTED"                                                     # Command + Decorator
    kinds = [e["kind"] for e in w.audit.sinks[0].events]
    assert "actuator_attempt" in kinds and w.metrics.counts["approved"] == 1
    assert w.metrics.acceptance_rate == 1.0
    assert [r.command for r in w.commands.history] == ["plan", "approve"]


def test_commands_record_failures_and_reject_is_not_undoable():
    w = compose.build(sinks=[MemorySink()])
    with pytest.raises(PermissionError):
        w.commands.run(ApproveCommand(w.agent, "nope", " "))
    assert w.commands.history[-1].ok is False
    p, _ = w.commands.run(PlanCommand(w.agent))
    w.commands.run(RejectCommand(w.agent, p.proposal_id, "ana"))
    with pytest.raises(NotUndoable):
        RejectCommand(w.agent, p.proposal_id, "ana").undo()


def test_plan_command_can_be_withdrawn_while_pending_only():
    w = compose.build(sinks=[MemorySink()])
    p, _ = w.commands.run(PlanCommand(w.agent))
    w.commands.undo_last()
    assert p.proposal_id not in w.agent.proposals
    p2, _ = w.commands.run(PlanCommand(w.agent))
    w.commands.run(ApproveCommand(w.agent, p2.proposal_id, "ana"))
    with pytest.raises(NotUndoable):
        w.commands.undo_last()
        w.commands.undo_last()
