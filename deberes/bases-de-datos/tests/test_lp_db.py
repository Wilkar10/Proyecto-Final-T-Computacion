"""Pruebas de los adaptadores ENTREGADOS (verdes)."""
from fakes import FakeConn

from lp_db.plugin import PgPriority, PgSink


def test_priority_reads_view_and_caches():
    conns = []

    def factory():
        c = FakeConn(rows=[(3,)])
        conns.append(c)
        return c

    p = PgPriority(factory, ttl_s=60)
    assert p.priority_of("Supermaxi Cumbayá") == 3.0
    assert p.priority_of("Supermaxi Cumbayá") == 3.0
    assert len(conns) == 1                                   # segunda lectura salió de la caché
    sql, params = conns[0].executed[0]
    assert "agent.v_customer_priority" in sql and params == ("Supermaxi Cumbayá",)  # parametrizado
    assert conns[0].closed


def test_priority_falls_back_when_unknown_or_db_down():
    assert PgPriority(lambda: FakeConn(rows=[]), 60).priority_of("desconocido") == 1.0

    def down():
        raise ConnectionError("sin red")

    assert PgPriority(down, 60).priority_of("x") == 1.0


def test_sink_maps_events_to_statements():
    conns = []

    def factory():
        c = FakeConn()
        conns.append(c)
        return c

    sink = PgSink(factory)
    prop = dict(proposal_id="p1", created_at="2026-11-24T10:00:00+00:00", robot="AMR-01", order_codes=["A", "B"], cost=20,
                budget=80, battery_before=100, algorithm="brute_force", exact=True, source="rule", status="PENDING_APPROVAL",
                decided_by=None, rationale="r")
    sink.write({"ts": "t", "kind": "proposal_created", "proposal": prop})
    sink.write({"ts": "t", "kind": "approved", "proposal_id": "p1", "by": "ana"})
    sink.write({"ts": "t", "kind": "executed", "proposal_id": "p1", "status": "EXECUTED"})
    sink.write({"ts": "t", "kind": "plan_started", "orders": 3})
    stmts = [[s for s, _ in c.executed] for c in conns]
    assert "ON CONFLICT (proposal_id) DO NOTHING" in stmts[0][1]          # idempotente
    assert stmts[1][1].startswith("UPDATE agent.proposal SET status") and conns[1].executed[1][1] == ("APPROVED", "ana", "p1")
    assert conns[2].executed[1][1] == ("EXECUTED", "p1")
    assert len(stmts[3]) == 1                                                # solo auditoría
    assert all(c.commits == 1 and c.closed for c in conns)


def test_sink_rolls_back_on_error():
    c = FakeConn(fail_on="agent.proposal")
    sink = PgSink(lambda: c)
    try:
        sink.write({"ts": "t", "kind": "approved", "proposal_id": "p", "by": "a"})
    except RuntimeError:
        pass
    assert c.rollbacks == 1 and c.commits == 0 and c.closed
