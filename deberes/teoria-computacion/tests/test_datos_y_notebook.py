import json
import os
import sys
from pathlib import Path

import pytest

from np_lab import datos, registro

AQUI = Path(__file__).resolve().parent.parent
NB = AQUI / "notebooks" / "02_teoria_sobre_el_lakehouse.ipynb"


def test_ejemplo_tiene_forma_del_lakehouse():
    op = datos.cargar("ejemplo", n=24)
    assert op.fuente == "ejemplo" and len(op.pedidos) == 24
    assert {"order_id", "customer_id", "segment", "zone_id", "kg", "window_min", "restante_min"} <= set(op.pedidos[0])
    assert all(any(z in s for s in op.cobertura.values()) for z in op.zonas)   # el ejemplo permite cubrir todo


def test_auto_sin_base_cae_a_ejemplo_y_lo_dice(monkeypatch):
    monkeypatch.setenv("PGHOST", "127.0.0.1")
    monkeypatch.setenv("PGPORT", "1")                       # puerto cerrado
    op = datos.cargar("auto", n=5)
    assert op.fuente == "ejemplo" and "EJEMPLO" in op.aviso
    with pytest.raises(Exception):
        datos.cargar("lakehouse", n=5)


def test_celdas_son_transitables_y_deterministas():
    rows = ["............", ".####..####.", "............", ".#..,,,..#..", ".#..,,,..#..", "............", ".####..####.", "............"]
    for cid in range(1, 40):
        x, y = datos.celda(cid, 1 + cid % 5, rows)
        assert rows[y][x] != "#"
        assert (x, y) == datos.celda(cid, 1 + cid % 5, rows)


def test_sql_es_valida_sintacticamente():
    pglast = pytest.importorskip("pglast")
    for q in (datos.SQL_PEDIDOS, datos.SQL_COBERTURA, datos.SQL_DEPOSITO_CON_MAS_PENDIENTES):
        pglast.parse_sql(q.replace("%(depot)s", "1").replace("%(n)s", "5").replace("%(min_n)s", "20"))
    pglast.parse_sql((AQUI.parent.parent / "base/lakehouse/sql/05_teoria.sql").read_text(encoding="utf-8"))


def test_registro_mide_calcula_brecha_y_exporta_csv():
    runs = []
    registro.medir(runs, "ejemplo", "tsp", "x", 5, False, lambda: 12, optimo=10)
    assert runs[0].brecha_pct == 20.0 and runs[0].segundos >= 0
    assert b"problema,algoritmo" in registro.a_csv(runs)
    assert registro.guardar_lake(runs) is False   # sin MinIO no falla, avisa


def test_notebook_es_json_valido_y_ejecuta_de_principio_a_fin(monkeypatch):
    os.environ["MPLBACKEND"] = "Agg"
    nb = json.loads(NB.read_text(encoding="utf-8"))
    assert nb["nbformat"] == 4 and len(nb["cells"]) > 20
    ns = {"display": lambda *a, **k: None, "__name__": "__main__"}
    monkeypatch.setattr(sys, "path", [str(AQUI), str(AQUI.parent.parent / "base/agent"), *sys.path])
    monkeypatch.setenv("PGPORT", "1")
    for i, c in enumerate(nb["cells"]):
        if c["cell_type"] == "code":
            src = "".join(c["source"]).replace("FUENTE = 'auto'", "FUENTE = 'ejemplo'")
            exec(compile(src, f"celda{i}", "exec"), ns)
    plazos = [r for r in ns["runs"] if r.problema == "plazos"]
    assert len(plazos) == 2
    hk_costo, dp = ns["c_hk"], next(r for r in plazos if r.algoritmo == "dp-plazos")
    assert dp.valor > hk_costo            # cumplir los plazos cuesta más que la ruta de mínima distancia (en el ejemplo)
