"""Raíz de composición: aquí (y solo aquí) se ensamblan los patrones. Variables: LP_STRATEGY=priority_first|closest_first|value_density."""
from __future__ import annotations

import os
from dataclasses import dataclass

from lpagent.agent import DispatchAgent
from lpagent.audit import JsonlSink, MemorySink
from lpagent.baseline import BaselineSolver, DryRunActuator, FixtureData

from .command import CommandBus
from .decorator import AuditedActuator, RetryingActuator
from .observer import ApproverNotifier, EventBus, MetricsObserver, ObservableAudit
from .strategy import PolicyPlanner, strategy_by_name
from .template import MarkdownRenderer


@dataclass
class Wiring:
    agent: DispatchAgent
    bus: EventBus
    commands: CommandBus
    metrics: MetricsObserver
    notifier: ApproverNotifier
    planner: PolicyPlanner
    audit: ObservableAudit


def build(data=None, solver=None, actuator=None, strategy: str | None = None, sinks=None, sleep=None) -> Wiring:
    data, solver = data or FixtureData(), solver or BaselineSolver()
    bus = EventBus()
    audit = ObservableAudit(bus, *(sinks if sinks is not None else [JsonlSink()]))
    # El orden de las capas es una decisión de diseño: Audited por FUERA registra cada intento visible al agente;
    # Retrying por DENTRO oculta los reintentos transitorios. Cambiarlo cambia lo que queda auditado.
    layered = AuditedActuator(RetryingActuator(actuator or DryRunActuator(), **({"sleep": sleep} if sleep else {})), audit)
    planner = PolicyPlanner(solver, strategy_by_name(strategy or os.getenv("LP_STRATEGY", "priority_first")))
    agent = DispatchAgent(data, solver, layered, audit, planner)
    metrics, notifier = MetricsObserver(), ApproverNotifier(MarkdownRenderer())
    bus.subscribe("*", metrics)
    bus.subscribe("proposal_created", notifier)
    return Wiring(agent, bus, CommandBus(), metrics, notifier, planner, audit)


def build_actuator():
    """Para LP_ACTUATOR_PLUGIN=lp_patterns.compose:build_actuator (el servidor base no tiene audit propio: solo reintentos)."""
    return RetryingActuator(DryRunActuator())
