"""Datos de operación para los ejercicios de Teoría.
Fuente 'lakehouse': Postgres del lakehouse (ods/master/dw). Fuente 'ejemplo': datos deterministas con la misma forma.
`cargar("auto")` intenta el lakehouse y, si no está disponible, usa el ejemplo y lo DICE (campo `fuente`/`aviso`).
Las SQL no se han ejecutado contra un Postgres real (solo su sintaxis); el lakehouse es sintético (lp.seed)."""
from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field
from pathlib import Path

SUP = json.loads((Path(__file__).parent / "supuestos_teoria.json").read_text(encoding="utf-8"))

SQL_PEDIDOS = """
SELECT o.order_id, c.customer_id, c.segment, c.zone_id,
       COALESCE(SUM(oi.qty * p.weight_kg), 0)::float AS kg,
       EXTRACT(EPOCH FROM (o.promised_at - o.created_at)) / 60 AS window_min,
       EXTRACT(EPOCH FROM (o.promised_at - now())) / 60 AS restante_min
FROM ods.orders o
JOIN master.customer c ON c.customer_id = o.customer_id
JOIN ods.order_items oi ON oi.order_id = o.order_id
JOIN master.product p ON p.product_id = oi.product_id
WHERE o.status = 'CREATED' AND o.depot_id = %(depot)s
GROUP BY o.order_id, c.customer_id, c.segment, c.zone_id, o.created_at, o.promised_at
ORDER BY o.created_at
LIMIT %(n)s
"""

SQL_DEPOSITO_CON_MAS_PENDIENTES = """
SELECT o.depot_id, d.name FROM ods.orders o JOIN master.depot d ON d.depot_id = o.depot_id
WHERE o.status = 'CREATED' GROUP BY o.depot_id, d.name ORDER BY COUNT(*) DESC LIMIT 1
"""

SQL_COBERTURA = """
SELECT ca.name AS carrier, z.zone_id, COUNT(*) AS n,
       AVG(CASE WHEN f.on_time THEN 1.0 ELSE 0.0 END) AS otif
FROM dw.fact_shipment f
JOIN dw.dim_carrier ca ON ca.carrier_key = f.carrier_key
JOIN dw.dim_customer dc ON dc.customer_key = f.customer_key
JOIN dw.dim_zone z ON z.zone_key = dc.zone_key
WHERE f.on_time IS NOT NULL
GROUP BY ca.name, z.zone_id
HAVING COUNT(*) >= %(min_n)s
"""


@dataclass
class Operacion:
    fuente: str
    deposito: str
    pedidos: list[dict]                      # order_id, customer_id, segment, zone_id, kg, window_min, restante_min
    cobertura: dict[str, set[int]]           # transportista -> zonas donde cumple el OTIF mínimo
    zonas: set[int]
    aviso: str = ""
    sup: dict = field(default_factory=lambda: SUP)

    def pesos_enteros(self) -> list[int]:
        return [max(1, round(p["kg"])) for p in self.pedidos]

    def prioridad(self, p: dict) -> int:
        return {"CORPORATE": 3, "PYME": 2}.get(p["segment"], 1)


def celda(customer_id: int, zone_id: int, rows: list[str]) -> tuple[int, int]:
    """SUPUESTO: celda del plano para un cliente = ancla de su zona + desplazamiento determinista, ajustada a celda transitable."""
    ax, ay = SUP["zona_celda"][str(zone_id)]
    rng = random.Random(customer_id * 7919 + zone_id)
    for _ in range(50):
        x, y = ax + rng.randint(-2, 2), ay + rng.randint(-1, 1)
        if 0 <= y < len(rows) and 0 <= x < len(rows[0]) and rows[y][x] != "#" and (x, y) != (0, 0):
            return x, y
    return ax, ay


def _ejemplo(n: int) -> Operacion:
    rng = random.Random(11)
    zonas = [1, 2, 3, 4, 5]                  # el depósito de ejemplo atiende 5 zonas, como CD Quito
    pedidos = []
    for i in range(n):
        seg = rng.choices(["RETAIL", "PYME", "CORPORATE"], weights=[0.55, 0.30, 0.15])[0]
        kg = sum(rng.randint(1, 12) * rng.uniform(0.2, 18) for _ in range(rng.randint(1, 5)))
        win = SUP["plazo_min_por_segmento"][seg]
        pedidos.append({"order_id": 100001 + i, "customer_id": rng.randint(1, 200), "segment": seg,
                        "zone_id": rng.choice(zonas), "kg": round(kg, 1), "window_min": win,
                        "restante_min": round(win * (1 - rng.uniform(0.3, 0.9)), 1)})
    cov: dict[str, set[int]] = {}
    for carrier, p in (("Flota Propia", 0.9), ("TransAndes", 0.7), ("RapidoCosta", 0.5), ("Condor Express", 0.6)):
        cov[carrier] = {z for z in range(1, 11) if rng.random() < p}
    for z in range(1, 11):                   # el ejemplo garantiza que todas las zonas se pueden cubrir
        if not any(z in s for s in cov.values()):
            cov["Flota Propia"].add(z)
    return Operacion("ejemplo", "CD Quito Carcelén (ejemplo)", pedidos, cov, set(range(1, 11)),
                     "Datos de ejemplo con la forma del lakehouse (no son del lakehouse).")


def _lakehouse(n: int) -> Operacion:
    import psycopg2  # noqa: PLC0415

    conn = psycopg2.connect(host=os.getenv("PGHOST", "localhost"), port=os.getenv("PGPORT", "5432"),
                            dbname=os.getenv("PGDATABASE", "logistpulse"), user=os.getenv("PGUSER", "lp_reader"),
                            password=os.getenv("PGPASSWORD", "lp_reader"), connect_timeout=3)
    with conn, conn.cursor() as cur:
        cur.execute(SQL_DEPOSITO_CON_MAS_PENDIENTES)
        row = cur.fetchone()
        if not row:
            raise RuntimeError("no hay pedidos CREATED en el lakehouse")
        depot_id, depot = row
        cur.execute(SQL_PEDIDOS, {"depot": depot_id, "n": n})
        cols = [c.name for c in cur.description]
        pedidos = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.execute(SQL_COBERTURA, {"min_n": SUP["min_envios_cobertura"]})
        cov: dict[str, set[int]] = {}
        zonas: set[int] = set()
        for carrier, zone, _n, otif in cur.fetchall():
            zonas.add(zone)
            if float(otif) >= SUP["otif_minimo_cobertura"]:
                cov.setdefault(carrier, set()).add(zone)
    return Operacion("lakehouse", depot, pedidos, cov, zonas)


def cargar(fuente: str = "auto", n: int = 24) -> Operacion:
    if fuente == "ejemplo":
        return _ejemplo(n)
    try:
        op = _lakehouse(n)
        if not op.pedidos:
            raise RuntimeError("consulta sin pedidos")
        return op
    except Exception as exc:  # noqa: BLE001
        if fuente == "lakehouse":
            raise
        op = _ejemplo(n)
        op.aviso = f"Lakehouse no disponible ({type(exc).__name__}); se usan datos de EJEMPLO."
        return op
