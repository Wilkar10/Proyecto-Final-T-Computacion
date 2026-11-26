"""Adaptadores para el agente:
   LP_DATA_PLUGIN=lp_db.plugin:build        -> prioridades desde agent.v_customer_priority (con caída elegante a 1.0)
   LP_AUDIT_PLUGIN=lp_db.plugin:build_sink  -> auditoría y propuestas en agent.audit_event / agent.proposal
"""
from __future__ import annotations

import json
import os
import time

from .pg import connect


class PgPriority:
    """Consulta con TTL. Si la base no responde o el cliente no está mapeado devuelve 1.0 (prioridad neutra)."""

    def __init__(self, connect_fn=connect, ttl_s: float = 60.0):
        self._connect, self.ttl_s = connect_fn, ttl_s
        self._cache: dict[str, tuple[float, float]] = {}
        self._warned = False

    def priority_of(self, customer: str) -> float:
        hit = self._cache.get(customer)
        if hit and time.monotonic() - hit[0] < self.ttl_s:
            return hit[1]
        try:
            conn = self._connect()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT priority FROM agent.v_customer_priority WHERE lab_customer = %s", (customer,))
                    row = cur.fetchone()
            finally:
                conn.close()
            value = float(row[0]) if row and row[0] is not None else 1.0
        except Exception as exc:  # noqa: BLE001 - la base caída no debe tumbar al agente
            if not self._warned:
                print(f"[lp_db] sin acceso al lakehouse, uso prioridad 1.0: {exc}")
                self._warned = True
            return 1.0
        self._cache[customer] = (time.monotonic(), value)
        return value


class PgSink:
    """Sumidero de auditoría: guarda cada evento y mantiene agent.proposal al día (idempotente)."""

    def __init__(self, connect_fn=connect):
        self._connect = connect_fn

    def write(self, event: dict) -> None:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO agent.audit_event (ts, kind, payload) VALUES (%s, %s, %s)",
                            (event["ts"], event["kind"], json.dumps(event, ensure_ascii=False, default=str)))
                kind = event["kind"]
                if kind == "proposal_created":
                    p = event["proposal"]
                    cur.execute(
                        "INSERT INTO agent.proposal (proposal_id, created_at, robot, order_codes, cost, budget, battery_before,"
                        " algorithm, exact, source, status, decided_by, rationale)"
                        " VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) ON CONFLICT (proposal_id) DO NOTHING",
                        (p["proposal_id"], p["created_at"], p["robot"], p["order_codes"], p["cost"], p["budget"],
                         p["battery_before"], p["algorithm"], p["exact"], p["source"], p["status"], p["decided_by"], p["rationale"]))
                elif kind in ("approved", "rejected"):
                    cur.execute("UPDATE agent.proposal SET status = %s, decided_by = %s WHERE proposal_id = %s",
                                ("APPROVED" if kind == "approved" else "REJECTED", event["by"], event["proposal_id"]))
                elif kind == "executed":
                    cur.execute("UPDATE agent.proposal SET status = %s WHERE proposal_id = %s",
                                (event["status"], event["proposal_id"]))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


def build():
    """Adaptador de datos: pedidos/robots del lab (LP_MODE=lab) o del fixture, con prioridad desde el lakehouse."""
    from lpagent.baseline import FixtureData, LabData

    prio = PgPriority()
    if os.getenv("LP_MODE", "fixture") == "lab":
        return LabData(priorities=prio.priority_of)
    data = FixtureData()
    data.priority_of = prio.priority_of
    return data


def build_sink():
    return PgSink()
