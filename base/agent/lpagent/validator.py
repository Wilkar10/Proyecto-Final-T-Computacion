"""Validador determinista V(problema, propuesta). El agente GENERA; este código DECIDE.
Todas las comprobaciones son de tiempo polinomial (en el tamaño de la propuesta), sin llamar al modelo."""
from __future__ import annotations

from .models import BATTERY_PER_COST, MIN_BATTERY, Robot, TripProblem

MAX_STOPS = 12  # tope duro: limita el costo del solver exacto y el daño de una propuesta errónea


def verify_certificate(problem: TripProblem, tour: list[int]) -> tuple[bool, str]:
    """Certificado del problema de decisión: tour es una permutación de 1..n y costo <= presupuesto."""
    if sorted(tour) != list(range(1, problem.n + 1)):
        return False, "el recorrido no es una permutación de todas las paradas"
    cost = problem.tour_cost(tour)
    if cost > problem.budget:
        return False, f"costo {cost} excede el presupuesto {problem.budget}"
    return True, f"costo {cost} <= presupuesto {problem.budget}"


def verify_proposal(problem: TripProblem, tour: list[int], robot: Robot, codes: list[str]) -> tuple[bool, list[str]]:
    """Reglas de negocio + certificado. Devuelve (ok, motivos de rechazo)."""
    errors: list[str] = []
    if not (1 <= problem.n <= MAX_STOPS):
        errors.append(f"número de paradas fuera de rango (1..{MAX_STOPS})")
    if robot.status != "IDLE":
        errors.append(f"robot {robot.code} no está libre ({robot.status})")
    if len(set(codes)) != len(codes):
        errors.append("pedidos duplicados")
    ok, why = verify_certificate(problem, tour) if not errors else (False, "")
    if not ok and why:
        errors.append(why)
    elif ok:
        need = problem.tour_cost(tour) * BATTERY_PER_COST
        if robot.battery - need < MIN_BATTERY:
            errors.append(f"batería insuficiente: {robot.battery} - {need:.0f} < reserva {MIN_BATTERY}")
    return (not errors), errors
