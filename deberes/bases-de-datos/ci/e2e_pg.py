"""Integración REAL contra Postgres (la corre ci-bd.yml): agente + PgPriority + PgSink con el rol lp_agent.
Sale con código != 0 si algo falla. No forma parte de pytest porque necesita la base viva."""
import os
import sys
import tempfile

import psycopg2

from lp_db.pg import connect
from lp_db.plugin import PgPriority, PgSink
from lpagent.agent import DispatchAgent
from lpagent.audit import Audit, JsonlSink
from lpagent.baseline import BaselineSolver, DryRunActuator, FixtureData


def scalar(sql, user="lp", password="lp_secret"):
    conn = connect(user, password)
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return cur.fetchone()[0]
    finally:
        conn.close()


def main() -> int:
    os.environ.setdefault("PGUSER", "lp_agent")
    os.environ.setdefault("PGPASSWORD", "lp_agent")
    prio = PgPriority(lambda: connect("lp_agent", "lp_agent"), ttl_s=0)
    assert prio.priority_of("Supermaxi Cumbayá") == 3.0, "CORPORATE debe valer 3"   # Cliente 001 del seed mínimo
    assert prio.priority_of("Farmacia Cruz Azul") == 2.0, "PYME debe valer 2"
    assert prio.priority_of("cliente-desconocido") == 1.0

    data = FixtureData()
    data.priority_of = prio.priority_of
    audit = Audit(JsonlSink(os.path.join(tempfile.mkdtemp(), "a.jsonl")), PgSink(lambda: connect("lp_agent", "lp_agent")))
    agent = DispatchAgent(data, BaselineSolver(), DryRunActuator(), audit)
    p, why = agent.plan()
    assert p, why
    agent.decide(p.proposal_id, "ci.bot", True)

    assert scalar(f"SELECT status FROM agent.proposal WHERE proposal_id = '{p.proposal_id}'") == "EXECUTED"
    assert scalar(f"SELECT decided_by FROM agent.proposal WHERE proposal_id = '{p.proposal_id}'") == "ci.bot"
    assert scalar("SELECT count(*) FROM agent.audit_event") >= 5

    # Mínimo privilegio: el rol del agente NO puede borrar ni alterar la auditoría
    for sql in ("DELETE FROM agent.audit_event", "UPDATE agent.audit_event SET kind = 'x'",
                "DELETE FROM agent.proposal", "UPDATE agent.proposal SET robot = 'x'"):
        try:
            conn = connect("lp_agent", "lp_agent")
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.rollback()
            print(f"FALLO: lp_agent pudo ejecutar: {sql}")
            return 1
        except psycopg2.errors.InsufficientPrivilege:
            pass
        finally:
            conn.close()
    print("e2e_pg OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
