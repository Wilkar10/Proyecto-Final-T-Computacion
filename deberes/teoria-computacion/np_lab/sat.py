"""SAT (clausal): literales +i / -i sobre variables 1..n. Asignación = dict {i: bool}."""
from __future__ import annotations

import itertools


def verify_sat(clauses, assignment: dict[int, bool]) -> bool:
    """V(φ, a): O(|φ|). Prueba de que SAT está en NP."""
    return all(any(assignment.get(abs(l), False) == (l > 0) for l in c) for c in clauses)


def brute_force(clauses, n_vars: int):
    """Exacto, O(2ⁿ·m). Devuelve una asignación o None."""
    for bits in itertools.product([False, True], repeat=n_vars):
        a = {i + 1: bits[i] for i in range(n_vars)}
        if verify_sat(clauses, a):
            return a
    return None


def dpll(clauses, n_vars: int):
    """DPLL con propagación unitaria y literal puro (opcional). Devuelve una asignación COMPLETA
    (todas las variables 1..n_vars) que satisfaga las cláusulas, o None si son insatisfacibles."""
    def simplify(cls, assign):
        """Propagación unitaria hasta punto fijo. Devuelve (cláusulas restantes, asignación) o (None, None) si hay conflicto."""
        while True:
            unit, rest_all = None, []
            for c in cls:
                if any(assign.get(abs(l)) == (l > 0) for l in c if abs(l) in assign):
                    continue                                   # cláusula ya satisfecha
                rest = tuple(l for l in c if abs(l) not in assign)
                if not rest:
                    return None, None                          # cláusula vacía = conflicto
                if len(rest) == 1 and unit is None:
                    unit = rest[0]
                rest_all.append(rest)
            cls = rest_all
            if unit is None:
                return cls, assign
            assign = {**assign, abs(unit): unit > 0}

    def solve(cls, assign):
        cls, assign = simplify(cls, assign)
        if cls is None:
            return None
        if not cls:
            return assign
        v = abs(cls[0][0])                                     # ramificación sobre una variable libre
        for val in (True, False):
            r = solve(cls, {**assign, v: val})
            if r is not None:
                return r
        return None

    r = solve([tuple(c) for c in clauses], {})
    return None if r is None else {i: r.get(i, False) for i in range(1, n_vars + 1)}
