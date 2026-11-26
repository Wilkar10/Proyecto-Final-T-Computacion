"""Olist (Kaggle: olistbr/brazilian-ecommerce): SLA, cancelaciones y flete de un marketplace real de Brasil.
Columnas usadas (documentadas por Olist): orders.csv -> order_id, customer_id, order_status,
order_purchase_timestamp, order_delivered_customer_date, order_estimated_delivery_date;
customers.csv -> customer_id, customer_state; order_items.csv -> order_id, price, freight_value.
SLA = entregado DESPUÉS de la fecha estimada (comparación por día)."""
from __future__ import annotations

import csv
import statistics as st
from collections import defaultdict
from datetime import datetime
from pathlib import Path

FAILED = {"canceled", "unavailable"}


def _dt(s: str):
    s = (s or "").strip()
    return datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S") if s else None


def _pct(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(q * (len(xs) - 1))))] if xs else float("nan")


def load(folder: str | Path, min_state_orders: int = 200) -> dict:
    d = Path(folder)
    state_of = {}
    cf = d / "olist_customers_dataset.csv"
    if cf.exists():
        with open(cf, newline="", encoding="utf-8") as f:
            state_of = {r["customer_id"]: r["customer_state"] for r in csv.DictReader(f)}
    n = failed = 0
    per_day: dict = defaultdict(int)
    late = deliv = 0
    actual, promised, lateness = [], [], []
    by_state = defaultdict(lambda: [0, 0])  # entregados, tardíos
    with open(d / "olist_orders_dataset.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            n += 1
            buy = _dt(r["order_purchase_timestamp"])
            if buy:
                per_day[buy.date()] += 1
            if r["order_status"] in FAILED:
                failed += 1
            got, est = _dt(r["order_delivered_customer_date"]), _dt(r["order_estimated_delivery_date"])
            if r["order_status"] == "delivered" and got and est and buy:
                deliv += 1
                is_late = got.date() > est.date()
                late += is_late
                actual.append((got - buy).total_seconds() / 86400)
                promised.append((est - buy).total_seconds() / 86400)
                if is_late:
                    lateness.append((got.date() - est.date()).days)
                s = state_of.get(r["customer_id"])
                if s:
                    by_state[s][0] += 1
                    by_state[s][1] += is_late
    out = {
        "fuente": "Olist (datos reales anonimizados, marketplace de Brasil, 2016-2018)",
        "pedidos": n,
        "pedidos_por_dia_prom": round(n / max(len(per_day), 1), 1),
        "pico_p95_sobre_media": round(_pct(list(per_day.values()), 0.95) / (n / max(len(per_day), 1)), 2) if per_day else None,
        "fallidos_pct": round(100 * failed / n, 2) if n else None,
        "entregados": deliv,
        "tardios_pct": round(100 * late / deliv, 2) if deliv else None,
        "dias_entrega_prom": round(st.mean(actual), 1) if actual else None,
        "dias_entrega_p90": round(_pct(actual, 0.9), 1) if actual else None,
        "dias_prometidos_prom": round(st.mean(promised), 1) if promised else None,
        "retraso_prom_dias_si_tarde": round(st.mean(lateness), 1) if lateness else None,
        "tardios_por_estado": {s: round(100 * v[1] / v[0], 1) for s, v in sorted(by_state.items()) if v[0] >= min_state_orders},
    }
    itf = d / "olist_order_items_dataset.csv"
    if itf.exists():
        price, freight = defaultdict(float), defaultdict(float)
        with open(itf, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                price[r["order_id"]] += float(r["price"] or 0)
                freight[r["order_id"]] += float(r["freight_value"] or 0)
        if price:
            out["flete_prom_por_pedido_brl"] = round(st.mean(freight.values()), 2)
            out["flete_sobre_precio_pct"] = round(100 * sum(freight.values()) / sum(price.values()), 1)
    return out
