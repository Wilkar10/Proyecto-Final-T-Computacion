"""Modelos de dominio del agente. Sin dependencias externas."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Supuesto de modelado (documentado en docs/ANALISIS_INTEGRACION.md): el lab descuenta 1 % de batería
# por unidad de costo de ruta. Para un recorrido cerrado, uso de batería = costo total del ciclo.
BATTERY_PER_COST = 1.0
MIN_BATTERY = 20  # mismo umbral que OrderService.MIN_BATTERY del lab: reserva al regresar


@dataclass(frozen=True)
class Stop:
    code: str
    x: int
    y: int
    priority: float = 1.0


@dataclass(frozen=True)
class Robot:
    code: str
    x: int
    y: int
    battery: int
    status: str = "IDLE"


@dataclass
class Context:
    """Foto del mundo que el agente puede leer (solo lectura)."""
    grid_rows: list[str]
    robots: list[Robot]
    orders: list[Stop]
    origin: tuple[int, int] = (0, 0)


@dataclass
class TripProblem:
    """Versión de DECISIÓN del recorrido: ¿existe un ciclo desde el origen que visite todas las
    paradas con costo <= budget?  dist es (n+1)x(n+1); el índice 0 es el origen y 1..n las paradas."""
    stops: list[Stop]
    dist: list[list[int]]
    budget: int

    @property
    def n(self) -> int:
        return len(self.stops)

    def tour_cost(self, order: list[int]) -> int:
        """Costo del ciclo 0 -> order[0] -> ... -> order[-1] -> 0 (índices 1..n)."""
        path = [0, *order, 0]
        return sum(self.dist[a][b] for a, b in zip(path, path[1:]))


@dataclass
class Solution:
    feasible: bool
    tour: Optional[list[int]] = None     # permutación de 1..n
    cost: Optional[int] = None
    algorithm: str = ""
    proven: bool = False                 # True: respuesta definitiva (algoritmo exacto). False: heurística.
    note: str = ""


@dataclass
class Proposal:
    proposal_id: str
    robot: str
    order_codes: list[str]               # en el orden del recorrido
    cost: int
    budget: int
    battery_before: int
    algorithm: str
    exact: bool
    rationale: str
    source: str = "rule"                 # rule | llm | fallback
    status: str = "PENDING_APPROVAL"     # PENDING_APPROVAL | APPROVED | REJECTED | EXECUTED | FAILED
    created_at: str = ""
    decided_by: Optional[str] = None
    detail: dict = field(default_factory=dict)
