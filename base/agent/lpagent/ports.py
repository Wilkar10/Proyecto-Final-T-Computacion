"""Puertos (interfaces). Cada deber reemplaza UN adaptador sin tocar a los demás:
   DataPort     -> Bases de Datos      (señales de prioridad desde el lakehouse)
   SolverPort   -> Teoría de la Comp.  (algoritmos para el problema tipo NP + verificador)
   ActuatorPort -> Desarrollo de SW    (cómo se ejecuta una propuesta aprobada en la API del lab)
"""
from __future__ import annotations

from typing import Protocol

from .models import Context, Proposal, Solution, TripProblem


class DataPort(Protocol):
    def load_context(self) -> Context: ...
    def priority_of(self, customer: str) -> float:
        """Prioridad >= 1 para un cliente (mayor = más urgente). Debe tolerar clientes desconocidos."""
        ...


class SolverPort(Protocol):
    name: str

    def solve(self, problem: TripProblem, time_limit_s: float) -> Solution: ...


class ActuatorPort(Protocol):
    def execute(self, proposal: Proposal) -> dict: ...


class LLMClient(Protocol):
    """Cliente mínimo de un modelo con herramientas. Devuelve una lista de bloques:
       {"type": "text", "text": ...} | {"type": "tool_use", "id": ..., "name": ..., "input": {...}}"""

    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> list[dict]: ...
