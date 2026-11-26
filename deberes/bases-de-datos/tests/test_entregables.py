"""Pruebas de los entregables del deber (verdes: el sistema ya está implementado). Ejecutar: pytest -v
Revisan estructura y sintaxis (pglast); la semántica contra el motor se comprueba con `make db-apply db-check`."""
import re
from pathlib import Path

import pytest
from fakes import FakeConn

HERE = Path(__file__).resolve().parent.parent


def read(rel):
    p = HERE / rel
    assert p.exists(), f"falta el entregable {rel}"
    return p.read_text(encoding="utf-8")


def parse(sql):
    pglast = pytest.importorskip("pglast")
    return pglast.parse_sql(sql)


# ---- B4 · ingesta idempotente y parametrizada
def test_ingest_is_idempotent_and_parameterized():
    from lp_db.ingest_lab import ingest_orders

    hostile = "LP-1'); DROP TABLE agent.proposal;--"
    orders = [dict(id=1, code=hostile, customer="Cliente X", destX=1, destY=2, status="CREATED", createdAt="2026-11-24T10:00:00Z"),
              dict(id=2, code="LP-2", customer="Cliente Y", destX=3, destY=4, status="CREATED", createdAt="2026-11-24T10:00:00Z")]
    conn = FakeConn()
    assert ingest_orders(conn, orders) == 2
    sqls = " ".join(s for s, _ in conn.executed)
    assert re.search(r"INSERT INTO ods\.lab_order", sqls, re.I) and re.search(r"ON CONFLICT \(code\) DO UPDATE", sqls, re.I)
    assert hostile not in sqls                                           # nunca interpolado en el texto SQL
    assert any(hostile in (p if isinstance(p, (list, tuple)) else tuple(p or ())) or hostile in str(p) for _, p in conn.executed)
    assert conn.commits == 1


def test_ingest_rolls_back_on_failure():
    from lp_db.ingest_lab import ingest_orders

    conn = FakeConn(fail_on="ods.lab_order")
    with pytest.raises(RuntimeError):
        ingest_orders(conn, [dict(id=1, code="A", customer="c", destX=0, destY=0, status="CREATED", createdAt="2026-11-24T10:00:00Z")])
    assert conn.rollbacks == 1 and conn.commits == 0


# ---- B1 · modelo normalizado
def test_b1_proposal_stop_table():
    sql = read("sql/10_proposal_stop.sql")
    parse(sql)
    assert re.search(r"CREATE TABLE (IF NOT EXISTS )?agent\.proposal_stop", sql, re.I)
    assert re.search(r"PRIMARY KEY", sql, re.I) and re.search(r"REFERENCES agent\.proposal", sql, re.I)


# ---- B3 · mart de KPIs
def test_b3_mart_agent_kpis():
    sql = read("sql/11_mart_agent.sql")
    parse(sql)
    assert re.search(r"CREATE (OR REPLACE )?(MATERIALIZED )?VIEW (IF NOT EXISTS )?mart_agent\.kpis", sql, re.I)
    for col in ("acceptance_rate", "fallback_share", "avg_budget_use"):
        assert col in sql, f"falta la columna {col}"


# ---- B4 · DDL de ingesta
def test_b4_lab_order_ddl():
    sql = read("sql/12_lab_ingest.sql")
    parse(sql)
    assert re.search(r"CREATE TABLE (IF NOT EXISTS )?ods\.lab_order", sql, re.I) and re.search(r"code\s+text.*(PRIMARY KEY|UNIQUE)|UNIQUE\s*\(code\)", sql, re.I | re.S)


# ---- B5 · pruebas de privilegios
def test_b5_privilege_tests():
    sql = read("sql/13_privilege_tests.sql")
    parse(sql)
    assert re.search(r"SET (SESSION |LOCAL )?ROLE lp_agent", sql, re.I)
    assert re.search(r"DELETE FROM agent\.audit_event", sql, re.I) and re.search(r"UPDATE agent\.audit_event", sql, re.I)
    assert re.search(r"insufficient_privilege", sql, re.I)               # cada intento prohibido debe CAPTURAR el error esperado


# ---- B2 · Data Trust Gate
def test_b2_at_least_six_checks_covering_dimensions():
    files = sorted((HERE / "checks").glob("dq_*.sql"))
    assert len(files) >= 6, f"hay {len(files)} controles; se piden >= 6"
    for f in files:
        stmts = parse(f.read_text(encoding="utf-8"))
        assert len(stmts) == 1 and type(stmts[0].stmt).__name__ == "SelectStmt", f"{f.name}: debe ser UNA consulta SELECT"
    text = " ".join(f.read_text(encoding="utf-8").lower() for f in files)
    for dim in ("completitud", "validez", "unicidad", "oportunidad", "consistencia"):
        assert dim in text, f"ningún control declara la dimensión «{dim}» en su comentario"


# ---- B6 · cadena de inventario → reposición → packing
def test_b6_inventory_chain_ddl_and_seed():
    ddl = read("sql/14_inventory_chain.sql")
    parse(ddl)
    for t in ("inv.sku", "inv.stock_level", "inv.stock_movement", "inv.purchase_order", "inv.packing_job", "inv.packing_box"):
        assert re.search(rf"CREATE TABLE IF NOT EXISTS {re.escape(t)}\b", ddl), f"falta la tabla {t}"
    assert re.search(r"BEFORE UPDATE OR DELETE ON inv\.stock_movement", ddl)          # libro de solo inserción
    assert "mart_ops.v_stock_coverage" in ddl and "mart_ops.v_packing_efficiency" in ddl
    seed = read("sql/15_inventory_seed.sql")
    parse(seed)
    assert seed.count("ON CONFLICT") >= 3                                            # idempotente


def test_b6_checks_cover_each_new_stage():
    for name in ("dq_08_stock_vs_movements", "dq_09_po_received_without_receipt", "dq_10_packing_integrity", "dq_11_stock_freshness"):
        sql = read(f"checks/{name}.sql")
        stmts = parse(sql)
        assert type(stmts[0].stmt).__name__ in ("SelectStmt",), name
    assert len(list((HERE / "checks").glob("dq_*.sql"))) >= 11


def test_b6_privilege_tests_cover_inventory():
    sql = read("sql/13_privilege_tests.sql")
    assert "inv.stock_movement" in sql and "inv.purchase_order" in sql
