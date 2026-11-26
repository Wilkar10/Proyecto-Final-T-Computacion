"""Cadena completa de Smart Inventory: inventario -> pedidos -> reposición -> packing -> (despacho).

Cada etapa tiene una política «manual» y una «sistema», de modo que se pueda medir qué aporta CADA etapa.
Es una simulación por días con supuestos explícitos (assumptions.json, bloque «cadena»); no es una predicción.

Flujo de un día:
  1. Llegan las órdenes de compra (reposición) que vencen hoy.
  2. Entran los pedidos del día. Cada línea reserva stock; si falta alguna línea, el pedido FALLA por falta de producto.
  3. Los pedidos completos se empacan en cajas (manual: first-fit en el orden del pedido; sistema: first-fit decreasing).
     El empaque tarda y a veces se equivoca (error de empaque): el pedido queda disponible para despachar más tarde.
  4. Se decide la reposición (manual: revisión periódica con pronóstico sesgado; sistema: punto de pedido con demanda observada).
  5. Se mide el costo de tener inventario ese día.
El despacho (rutas, robots) sigue en sim.py: usa la hora en que el pedido quedó listo (Order.avail).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

REPL = ("manual", "sistema")
PACK = ("manual", "sistema")
NEVER = float("inf")


def sku_weights(n: int) -> list[float]:
    """Popularidad tipo Pareto suave: pocos SKU concentran la demanda."""
    w = [1 / (i + 1) for i in range(n)]
    s = sum(w)
    return [x / s for x in w]


def sku_volume(i: int) -> int:
    return 1 + (i * 7) % 4                      # 1..4 unidades de volumen por pieza, determinista


def first_fit(items: list[int], cap: int) -> list[int]:
    """Devuelve el nivel de llenado de cada caja, colocando en el orden recibido."""
    boxes: list[int] = []
    for it in items:
        for k, used in enumerate(boxes):
            if used + it <= cap:
                boxes[k] += it
                break
        else:
            boxes.append(it)
    return boxes


def first_fit_decreasing(items: list[int], cap: int) -> list[int]:
    return first_fit(sorted(items, reverse=True), cap)


def validate_cadena(a: dict, repl: str, pack: str) -> None:
    if repl not in REPL or pack not in PACK:
        raise ValueError(f"reposición {REPL}, packing {PACK}")
    c = a["cadena"]
    if c["skus"] < 1 or c["box_capacity"] < max(sku_volume(i) for i in range(c["skus"])):
        raise ValueError("la caja debe poder contener al menos una pieza de cada SKU")


@dataclass
class Cadena:
    a: dict
    repl: str
    pack: str
    seed: int
    stock: list[float] = field(default_factory=list)
    on_order: list[list[tuple[int, float]]] = field(default_factory=list)     # por SKU: (día de llegada, cantidad)
    history: list[list[float]] = field(default_factory=list)                  # demanda observada por día y SKU
    prior: list[float] = field(default_factory=list)

    def __post_init__(self):
        validate_cadena(self.a, self.repl, self.pack)
        c = self.a["cadena"]
        n = c["skus"]
        w = sku_weights(n)
        per_day = self.a["orders_per_day"] * (sum(c["lines_per_order"]) / 2) * (sum(c["qty_per_line"]) / 2)
        self.true_mean = [per_day * x for x in w]                              # unidades/día por SKU (esperanza)
        bias = c["manual"]["forecast_bias"]
        self.prior = [m * (1 + bias) for m in self.true_mean]                  # pronóstico del comprador manual
        self.stock = [m * c["initial_cover_days"] for m in self.true_mean]
        self.on_order = [[] for _ in range(n)]
        self.w = w

    # ---------------------------------------------------------------- un día
    def run_day(self, day: int, orders: list, m, horizon_min: float) -> None:
        c = self.a["cadena"]
        ch = m.chain
        for k in ("pedidos", "falta_producto", "error_empaque", "cajas", "volumen_piezas", "volumen_cajas",
                  "ordenes_compra", "min_reposicion", "min_empaque", "unidades_dia_inventario"):
            ch.setdefault(k, 0.0)
        n = c["skus"]
        for s in range(n):                                                     # 1. llegan órdenes de compra
            arr = [q for d, q in self.on_order[s] if d <= day]
            self.stock[s] += sum(arr)
            self.on_order[s] = [(d, q) for d, q in self.on_order[s] if d > day]

        rng = random.Random(self.seed * 5003 + day * 17 + 1)                  # MISMA demanda para toda política
        demand = [0.0] * n
        pk = c[self.pack] if self.pack in c else c["manual"]
        for o in orders:                                                       # 2. pedidos
            ch["pedidos"] += 1
            lines = [(rng.choices(range(n), self.w)[0], rng.randint(*c["qty_per_line"]))
                     for _ in range(rng.randint(*c["lines_per_order"]))]
            err_roll = rng.random()                                            # se sortea siempre: la demanda no depende de la política
            for s, q in lines:
                demand[s] += q
            if any(self.stock[s] < q for s, q in lines):                       # falta producto: el pedido no sale completo
                ch["falta_producto"] += 1
                o.avail = NEVER
                continue
            for s, q in lines:
                self.stock[s] -= q
            items = [sku_volume(s) for s, q in lines for _ in range(q)]        # 3. packing
            boxes = (first_fit_decreasing if self.pack == "sistema" else first_fit)(items, c["box_capacity"])
            ch["cajas"] += len(boxes)
            ch["volumen_piezas"] += sum(items)
            ch["volumen_cajas"] += len(boxes) * c["box_capacity"]
            minutes = pk["pack_min_fixed"] + pk["pack_min_per_box"] * len(boxes)
            ch["min_empaque"] += minutes
            ready = o.created + minutes
            if err_roll < pk["pack_error_rate"]:                               # se empacó mal: se rehace
                ch["error_empaque"] += 1
                ready += self.a["manual"]["rework_delay_min"]
            o.avail = max(o.avail, ready)
        self.history.append(demand)

        self._reorder(day, ch)                                                 # 4. reposición
        ch["unidades_dia_inventario"] += sum(self.stock)                       # 5. costo de tener inventario

    def _estimate(self, s: int) -> float:
        if self.repl == "manual" or len(self.history) < 3:
            return self.prior[s]
        w = self.a["cadena"]["sistema"]["window_days"]
        h = self.history[-w:]
        return sum(d[s] for d in h) / len(h)

    def _reorder(self, day: int, ch: dict) -> None:
        c = self.a["cadena"]
        p = c[self.repl]
        for s in range(c["skus"]):
            pos = self.stock[s] + sum(q for _, q in self.on_order[s])
            est = self._estimate(s)
            if self.repl == "manual":
                due = (day % p["review_every_days"]) == 0
                ch["min_reposicion"] += p["min_per_sku_review"] if due else 0.0
            else:
                due = pos <= est * (c["lead_time_days"] + p["safety_days"])
            if not due:
                continue
            qty = math.ceil(est * p["order_up_to_days"] - pos)
            if qty <= 0:
                continue
            self.on_order[s].append((day + c["lead_time_days"], float(qty)))
            ch["ordenes_compra"] += 1
            if self.repl == "sistema":
                ch["min_reposicion"] += p["min_per_po_review"]
