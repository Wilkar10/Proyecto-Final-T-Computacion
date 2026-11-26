"""Registro de corridas de algoritmos: lista en memoria + (opcional) Postgres `teoria.solver_run` + Data Lake (CSV en MinIO)."""
from __future__ import annotations

import csv
import io
import os
import time
from dataclasses import asdict, dataclass

CAMPOS = ["problema", "algoritmo", "n", "exacto", "valor", "optimo", "brecha_pct", "segundos", "fuente"]


@dataclass
class Corrida:
    problema: str
    algoritmo: str
    n: int
    exacto: bool
    valor: float | None
    optimo: float | None
    brecha_pct: float | None
    segundos: float
    fuente: str


def medir(runs: list, fuente: str, problema: str, algoritmo: str, n: int, exacto: bool, fn, optimo=None, valor_de=lambda r: r):
    """Ejecuta fn(), mide el tiempo, calcula la brecha contra `optimo` (si se da) y registra la corrida. Devuelve el resultado de fn."""
    t0 = time.perf_counter()
    res = fn()
    dt = time.perf_counter() - t0
    v = valor_de(res)
    brecha = None
    if optimo not in (None, 0) and v is not None:
        brecha = round(100 * abs(v - optimo) / abs(optimo), 2)
    runs.append(Corrida(problema, algoritmo, n, exacto, v, optimo, brecha, round(dt, 6), fuente))
    return res


def a_csv(runs) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CAMPOS)
    w.writeheader()
    w.writerows(asdict(r) for r in runs)
    return buf.getvalue().encode("utf-8")


def guardar_postgres(runs) -> bool:
    """Escribe en teoria.solver_run (requiere un rol con INSERT, p. ej. el dueño `lp`). Devuelve False si no hay base."""
    try:
        import psycopg2  # noqa: PLC0415
        conn = psycopg2.connect(host=os.getenv("PGHOST", "localhost"), port=os.getenv("PGPORT", "5432"),
                                dbname=os.getenv("PGDATABASE", "logistpulse"), user=os.getenv("PGWRITER", "lp"),
                                password=os.getenv("PGWRITER_PASSWORD", "lp_secret"), connect_timeout=3)
        with conn, conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO teoria.solver_run (problema, algoritmo, n, exacto, valor, optimo, brecha_pct, segundos, fuente) "
                "VALUES (%(problema)s, %(algoritmo)s, %(n)s, %(exacto)s, %(valor)s, %(optimo)s, %(brecha_pct)s, %(segundos)s, %(fuente)s)",
                [asdict(r) for r in runs])
        return True
    except Exception:  # noqa: BLE001
        return False


def guardar_lake(runs, key: str = "teoria/solver_runs.csv") -> bool:
    """Deja el CSV en la zona curada del Data Lake (lake-curated). Solo funciona dentro del contenedor Jupyter (usa lp.common)."""
    try:
        from lp.common import CURATED, put_bytes  # noqa: PLC0415
        put_bytes(CURATED, key, a_csv(runs))
        return True
    except Exception:  # noqa: BLE001
        return False
