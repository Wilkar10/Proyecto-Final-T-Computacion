"""Corporación Favorita (Kaggle: store-sales-time-series-forecasting / favorita-grocery-sales-forecasting).
Usa transactions.csv (date, store_nbr, transactions): forma de la demanda diaria de un retailer ecuatoriano.
Es DEMANDA, no despacho: sirve para el patrón (pico, día de la semana), no para SLA ni costos."""
from __future__ import annotations

import csv
import statistics as st
from collections import defaultdict
from datetime import date
from pathlib import Path

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def load(folder: str | Path) -> dict:
    daily = defaultdict(int)
    stores = set()
    with open(Path(folder) / "transactions.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            daily[date.fromisoformat(r["date"])] += int(float(r["transactions"]))
            stores.add(r["store_nbr"])
    vals = sorted(daily.values())
    mean = st.mean(vals)
    wd = defaultdict(list)
    for d, v in daily.items():
        wd[d.weekday()].append(v)
    return {
        "fuente": "Corporación Favorita (retailer de Ecuador): transacciones diarias",
        "dias": len(daily),
        "tiendas": len(stores),
        "inicio": min(daily).isoformat(),
        "fin": max(daily).isoformat(),
        "pico_p95_sobre_media": round(vals[int(0.95 * (len(vals) - 1))] / mean, 2),
        "max_sobre_media": round(vals[-1] / mean, 2),
        "coef_variacion": round(st.pstdev(vals) / mean, 2),
        "indice_por_dia": {DIAS[k]: round(st.mean(v) / mean, 2) for k, v in sorted(wd.items())},
    }
