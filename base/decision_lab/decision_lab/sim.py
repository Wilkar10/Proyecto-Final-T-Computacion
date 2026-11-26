from __future__ import annotations

import json
import random
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from lpagent.grid import DEFAULT_LAYOUT, dijkstra, walkable
from lpagent.models import BATTERY_PER_COST, MIN_BATTERY, Robot, TripProblem, Stop
from lpagent.validator import verify_proposal

from .cadena import Cadena

GRID = DEFAULT_LAYOUT
ORIGIN = (0, 0)
DEFAULT_ASSUMPTIONS = Path(__file__).with_name("assumptions.json")


def load_assumptions(path: str | Path | None = None, overrides: dict | None = None) -> dict:
    a = json.loads(Path(path or DEFAULT_ASSUMPTIONS).read_text(encoding="utf-8"))
    for k, v in (overrides or {}).items():
        a[k] = {**a[k], **v} if isinstance(v, dict) else v
    return a


@lru_cache(maxsize=None)
def _dist_from(src):
    return dijkstra(GRID, src)


def matrix(points):
    return [[_dist_from(p)[q] for q in points] for p in points]


# ------------------------------------------------------------------ solver exacto pequeño (Held-Karp) y heurístico
def held_karp(dist):
    n = len(dist) - 1
    INF = 10**9
    dp = [[INF] * n for _ in range(1 << n)]
    par = [[-1] * n for _ in range(1 << n)]
    for j in range(n):
        dp[1 << j][j] = dist[0][j + 1]
    for m in range(1, 1 << n):
        for j in range(n):
            if dp[m][j] >= INF or not m >> j & 1:
                continue
            for k in range(n):
                if not m >> k & 1:
                    c = dp[m][j] + dist[j + 1][k + 1]
                    if c < dp[m | 1 << k][k]:
                        dp[m | 1 << k][k], par[m | 1 << k][k] = c, j
    full = (1 << n) - 1
    cost, last = min((dp[full][j] + dist[j + 1][0], j) for j in range(n))
    tour, m = [], full
    while last != -1:
        tour.append(last + 1)
        prev = par[m][last]
        m ^= 1 << last
        last = prev
    return tour[::-1], cost


def nearest_neighbor(dist):
    left, cur, tour = set(range(1, len(dist))), 0, []
    while left:
        nxt = min(left, key=lambda j: dist[cur][j])
        tour.append(nxt)
        left.remove(nxt)
        cur = nxt
    return tour, sum(dist[a][b] for a, b in zip([0, *tour], [*tour, 0]))


# ------------------------------------------------------------------ dominio
@dataclass
class Order:
    code: str
    x: int
    y: int
    segment: str
    priority: int
    created: float
    deadline: float
    avail: float = 0.0
    delivered: float | None = None
    planned: bool = False


@dataclass
class Rob:
    code: str
    battery: float
    free_at: float = 0.0


@dataclass
class Metrics:
    policy: str
    orders: int = 0
    on_time: int = 0
    late: int = 0
    undelivered: int = 0
    failed_orders: int = 0
    failed_trips: int = 0
    failed_error: int = 0
    trips: int = 0
    move_cost_units: float = 0.0
    wasted_cost_units: float = 0.0
    plan_minutes: float = 0.0
    validator_rejections: int = 0
    approvals: int = 0          # viajes que esperaron la aprobación de una persona
    auto_trips: int = 0         # viajes que salieron sin aprobación (solo nivel 2, bajo riesgo)
    by_segment: dict = field(default_factory=dict)
    chain: dict = field(default_factory=dict)    # contadores de la cadena (vacío si no se modela)


def gen_orders(a: dict, rng: random.Random, day: int) -> list[Order]:
    cells = [(x, y) for y in range(len(GRID)) for x in range(len(GRID[0])) if walkable(GRID, x, y) and (x, y) != ORIGIN]
    segs = list(a["segments"])
    weights = [a["segments"][s]["share"] for s in segs]
    out = []
    for i in range(a["orders_per_day"]):
        seg = rng.choices(segs, weights)[0]
        t = rng.uniform(0, a["arrival_window_min"])
        x, y = rng.choice(cells)
        out.append(Order(f"D{day}-{i:03d}", x, y, seg, a["segments"][seg]["priority"], t, t + a["segments"][seg]["sla_min"]))
    return sorted(out, key=lambda o: o.created)


# ------------------------------------------------------------------ políticas de selección (Strategy, versión del laboratorio)
POLICIES = {
    "manual_fifo": None,
    "sistema_prioridad": lambda o, t: (-o.priority, o.created),
    "sistema_cercania": lambda o, t: (abs(o.x) + abs(o.y), o.created),
    "sistema_plazo": lambda o, t: (o.deadline, o.created),                 # el más urgente primero (EDF)
    "sistema_plazo_heuristico": lambda o, t: (o.deadline, o.created),      # igual, pero con vecino más cercano (sin óptimo)
}


def _tour_cost(dist, order):
    return sum(dist[a][b] for a, b in zip([0, *order], [*order, 0]))


def simulate(policy: str, a: dict, days: int = 20, seed: int = 1, autonomy: int | None = None,
             chain: tuple[str, str] | None = None) -> Metrics:
    """autonomy=None: comportamiento original (sin modelar aprobaciones). 1: una persona aprueba CADA viaje.
    2: solo se aprueban los viajes de riesgo (más de low_risk_max_stops paradas, algún pedido CORPORATE o poca batería sobrante)."""
    if autonomy not in (None, 1, 2):
        raise ValueError("autonomy debe ser None, 1 o 2")
    if policy not in POLICIES:
        raise ValueError(f"política desconocida: {policy}; opciones: {sorted(POLICIES)}")
    manual = policy == "manual_fifo"
    cad = Cadena(a, chain[0], chain[1], seed) if chain else None            # inventario → reposición → packing
    if manual and autonomy is not None:
        raise ValueError("la política manual no tiene nivel de autonomía")
    m = Metrics(policy if autonomy is None else f"{policy} · nivel {autonomy}")
    p_err = (a["manual"] if manual else a["system"])["error_rate"]
    for day in range(days):
        orders = gen_orders(a, random.Random(seed * 100003 + day), day)          # MISMOS pedidos para todas las políticas
        err_rng = random.Random(seed * 7919 + day)
        batt_rng = random.Random(seed * 31 + day)
        robots = [Rob(f"R{i+1}", batt_rng.uniform(70, 100)) for i in range(a["robots"])]
        m.orders += len(orders)
        if cad:
            cad.run_day(day, orders, m, a["horizon_min"])
        t = 0.0
        while t <= a["horizon_min"] and any(o.delivered is None for o in orders):
            pending = [o for o in orders if o.delivered is None and o.created <= t and o.avail <= t]
            for r in sorted(robots, key=lambda r: -r.battery):
                if r.free_at > t:
                    continue
                if r.battery < a["charge_threshold"]:
                    r.battery, r.free_at = 100.0, t + a["charge_min"]
                    continue
                if not pending:
                    continue
                budget = int(r.battery - MIN_BATTERY)
                group = _manual_group(pending, a, r) if manual else _system_group(pending, r, budget, t, policy, a, m)
                if not group:
                    if r.battery < 95:                                  # nada cabe con esta carga: se envía a cargar
                        r.battery, r.free_at = 100.0, t + a["charge_min"]
                    continue
                for o in group:
                    pending.remove(o)
                _execute(group, r, t, a, m, manual, p_err, err_rng, pending, policy, autonomy)
            t += a["wave_min"]
        for o in orders:
            if o.delivered is None:
                m.undelivered += 1
            elif o.delivered <= o.deadline:
                m.on_time += 1
                _seg(m, o.segment, "on_time")
            else:
                m.late += 1
            _seg(m, o.segment, "orders")
    return m


def _seg(m, seg, key):
    m.by_segment.setdefault(seg, {"orders": 0, "on_time": 0})[key] += 1


def _manual_group(pending, a, robot):
    """El despachador toma los pedidos más antiguos y, si su estimación no cabe en la batería, quita el último y reintenta."""
    fifo = sorted(pending, key=lambda o: o.created)[: a["manual"]["group_size"]]
    budget = robot.battery - MIN_BATTERY
    for k in range(len(fifo), 0, -1):
        d = matrix([ORIGIN] + [(o.x, o.y) for o in fifo[:k]])
        if _tour_cost(d, list(range(1, k + 1))) * (1 - a["manual"]["cost_underestimate"]) <= budget:
            return fifo[:k]
    return []


def _system_group(pending, robot, budget, t, policy, a, m):
    key = POLICIES[policy]
    chosen: list[Order] = []
    for cand in sorted(pending, key=lambda o: key(o, t))[:12]:                           # acota el costo de cálculo
        if len(chosen) >= a["system"]["max_stops"]:
            break
        trial = chosen + [cand]
        d = matrix([ORIGIN] + [(o.x, o.y) for o in trial])
        _, c = (nearest_neighbor(d) if policy.endswith("heuristico") else held_karp(d))
        if c <= budget:
            chosen.append(cand)
    return chosen


def _execute(group, r, t, a, m, manual, p_err, err_rng, pending, policy, autonomy=None):
    mm = a["manual"] if manual else a["system"]
    pts = [ORIGIN] + [(o.x, o.y) for o in group]
    d = matrix(pts)
    if manual:
        order = list(range(1, len(group) + 1))                                           # FIFO: sin optimizar el recorrido
        cost = _tour_cost(d, order)
        for o in group:                                                                  # el tiempo de planificar se paga una vez por pedido
            if not o.planned:
                o.planned = True
                m.plan_minutes += a["manual"]["plan_min_per_order"]
    else:
        order, cost = (nearest_neighbor(d) if policy.endswith("heuristico") else held_karp(d))
        problem = TripProblem([Stop(o.code, o.x, o.y) for o in group], d, int(r.battery - MIN_BATTERY))
        ok, _ = verify_proposal(problem, order, Robot(r.code, 0, 0, int(r.battery)), [o.code for o in group])
        m.plan_minutes += a["system"]["review_min_per_trip"]
        if not ok:                                                                       # el validador frena: no se despacha
            m.validator_rejections += 1
            pending.extend(group)
            return
    delay = 0.0
    if autonomy is not None:                                                             # modelo de aprobación humana
        au = a["autonomy"]
        low_risk = (len(group) <= au["low_risk_max_stops"] and max(o.priority for o in group) < 3
                    and r.battery - cost * BATTERY_PER_COST >= MIN_BATTERY + au["low_risk_battery_margin"])
        if autonomy == 1 or not low_risk:
            delay = au["approval_delay_min"]                                             # el robot espera la decisión
            p_err = p_err * (1 - au["human_catch_rate"])                                 # la persona atrapa parte de los errores
            m.approvals += 1
            m.plan_minutes += au["approval_min_per_trip"]
        else:
            m.auto_trips += 1
    t_go = t + delay
    m.trips += 1
    if manual and cost * BATTERY_PER_COST > r.battery - MIN_BATTERY:                    # viaje abortado: falla de despacho
        waste = cost * mm["abort_fraction"]
        r.battery -= waste * BATTERY_PER_COST
        r.free_at = t + waste * a["min_per_cost_unit"] + mm["abort_min"]
        m.failed_trips += 1
        m.failed_orders += len(group)
        m.wasted_cost_units += waste
        for o in group:
            o.avail = t + mm["rework_delay_min"]
        pending.extend(group)
        return
    cum, prev = 0.0, 0
    for idx in order:
        cum += d[prev][idx]
        prev = idx
        o = group[idx - 1]
        if err_rng.random() < p_err:                                                     # error humano/de integración
            m.failed_orders += 1
            m.failed_error += 1
            o.avail = t + a["manual"]["rework_delay_min"]
            pending.append(o)
            continue
        o.delivered = t_go + cum * a["min_per_cost_unit"]
    r.battery -= cost * BATTERY_PER_COST
    r.free_at = t_go + cost * a["min_per_cost_unit"]
    m.move_cost_units += cost


# ------------------------------------------------------------------ KPIs y dinero
def kpis(m: Metrics, a: dict, days: int) -> dict:
    mo = a["money"]
    plan_h = m.plan_minutes / 60
    cost = {
        "movimiento": (m.move_cost_units + m.wasted_cost_units) * mo["cost_per_cost_unit_usd"],
        "retrabajo": m.failed_orders * mo["rework_cost_per_failed_order_usd"],
        "penalidad_sla": (m.late + m.undelivered) * mo["late_penalty_per_order_usd"],
        "personal_planificacion": plan_h * mo["planner_hourly_usd"],
    }
    ch = _chain_kpis(m, a, days, cost) if m.chain else {}
    return {
        "policy": m.policy,
        "fallidos_pct": 100 * m.failed_orders / m.orders,
        "fallidos_bateria_pct": 100 * (m.failed_orders - m.failed_error) / m.orders,
        "fallidos_error_pct": 100 * m.failed_error / m.orders,
        "sla_pct": 100 * m.on_time / m.orders,
        "sla_corporate_pct": 100 * m.by_segment.get("CORPORATE", {"on_time": 0, "orders": 1})["on_time"] / max(1, m.by_segment.get("CORPORATE", {"orders": 1})["orders"]),
        "sin_entregar_pct": 100 * m.undelivered / m.orders,
        "horas_planificacion_dia": plan_h / days,
        "costo_dia_usd": sum(cost.values()) / days,
        "costo_por_pedido_usd": sum(cost.values()) / m.orders,
        "componentes_dia_usd": {k: v / days for k, v in cost.items()},
        "validator_rejections": m.validator_rejections,
        "aprobaciones_dia": m.approvals / days,
        "viajes_autonomos_pct": 100 * m.auto_trips / max(1, m.approvals + m.auto_trips),
        **ch,
    }


def _chain_kpis(m: Metrics, a: dict, days: int, cost: dict) -> dict:
    """Suma al costo las etapas de inventario, compras, empaque y quiebres (modifica `cost` para que el total sea coherente)."""
    mo, ch, c = a["money"], m.chain, a["cadena"]
    cost["inventario"] = ch["unidades_dia_inventario"] * mo["holding_usd_per_unit_day"]
    cost["compras"] = ch["ordenes_compra"] * mo["po_fixed_usd"]
    cost["empaque"] = ch["cajas"] * mo["box_usd"] + ch["min_empaque"] / 60 * mo["packer_hourly_usd"] + ch["error_empaque"] * mo["rework_cost_per_failed_order_usd"]
    cost["reposicion_personal"] = ch["min_reposicion"] / 60 * mo["buyer_hourly_usd"]
    cost["quiebres"] = ch["falta_producto"] * mo["stockout_cost_per_order_usd"]
    n = max(1, ch["pedidos"])
    return {
        "falta_producto_pct": 100 * ch["falta_producto"] / n,
        "error_empaque_pct": 100 * ch["error_empaque"] / n,
        "fallidos_total_pct": 100 * (ch["falta_producto"] + ch["error_empaque"] + m.failed_orders) / n,
        "nivel_servicio_pct": 100 * (1 - ch["falta_producto"] / n),
        "cajas_por_pedido": ch["cajas"] / max(1, n - ch["falta_producto"]),
        "llenado_cajas_pct": 100 * ch["volumen_piezas"] / ch["volumen_cajas"] if ch["volumen_cajas"] else 0.0,
        "cobertura_dias": (ch["unidades_dia_inventario"] / days) / max(1e-9, sum(Cadena(a, "manual", "manual", 1).true_mean)),
        "horas_persona_cadena_dia": (ch["min_reposicion"] + ch["min_empaque"]) / 60 / days,
        "ordenes_compra_dia": ch["ordenes_compra"] / days,
        "componentes_dia_usd": {k: v / days for k, v in cost.items()},
        "costo_dia_usd": sum(cost.values()) / days,
        "costo_por_pedido_usd": sum(cost.values()) / m.orders,
    }


def compare(a: dict, policies=None, days: int = 20, seed: int = 1, autonomy: int | None = None) -> dict:
    policies = policies or list(POLICIES)
    rows = [kpis(simulate(p, a, days, seed, autonomy if p != "manual_fifo" else None), a, days) for p in policies]
    base = rows[0] if rows[0]["policy"] == "manual_fifo" else None
    for r in rows:
        if base:
            r["ahorro_mes_usd"] = (base["costo_dia_usd"] - r["costo_dia_usd"]) * a["money"]["working_days_per_month"]
            r["horas_liberadas_dia"] = base["horas_planificacion_dia"] - r["horas_planificacion_dia"]
            r["fte_liberados"] = r["horas_liberadas_dia"] / 8
    return {"days": days, "seed": seed, "rows": rows}


def compare_autonomy(a: dict, policy: str = "sistema_plazo", days: int = 20, seed: int = 1) -> dict:
    """Misma política y mismos pedidos, con el agente en nivel 1 (aprueban todo) y nivel 2 (solo lo riesgoso); la fila manual es la referencia."""
    rows = [kpis(simulate("manual_fifo", a, days, seed), a, days)]
    rows += [kpis(simulate(policy, a, days, seed, autonomy=n), a, days) for n in (1, 2)]
    base = rows[0]
    for r in rows:
        r["ahorro_mes_usd"] = (base["costo_dia_usd"] - r["costo_dia_usd"]) * a["money"]["working_days_per_month"]
        r["fte_liberados"] = (base["horas_planificacion_dia"] - r["horas_planificacion_dia"]) / 8
    return {"days": days, "seed": seed, "rows": rows}


def compare_cadena(a: dict, days: int = 20, seed: int = 1, autonomy: int | None = None) -> dict:
    """Escalera de decisiones: se mejora UNA etapa a la vez para ver qué aporta cada una (misma demanda en todas las filas)."""
    steps = [("0 · todo manual", "manual_fifo", ("manual", "manual")),
             ("1 · + reposición con punto de pedido", "manual_fifo", ("sistema", "manual")),
             ("2 · + packing optimizado", "manual_fifo", ("sistema", "sistema")),
             ("3 · + despacho optimizado", "sistema_plazo", ("sistema", "sistema"))]
    rows = []
    for label, pol, ch in steps:
        r = kpis(simulate(pol, a, days, seed, autonomy if pol != "manual_fifo" else None, chain=ch), a, days)
        r["policy"] = label
        rows.append(r)
    base = rows[0]
    for r in rows:
        r["ahorro_mes_usd"] = (base["costo_dia_usd"] - r["costo_dia_usd"]) * a["money"]["working_days_per_month"]
        r["horas_liberadas_dia"] = (base["horas_planificacion_dia"] + base["horas_persona_cadena_dia"]
                                    - r["horas_planificacion_dia"] - r["horas_persona_cadena_dia"])
        r["fte_liberados"] = r["horas_liberadas_dia"] / 8
    return {"days": days, "seed": seed, "rows": rows}
