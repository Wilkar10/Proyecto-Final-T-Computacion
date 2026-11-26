"""Ingesta lab -> lakehouse. Carga los pedidos del lab a ods.lab_order de forma IDEMPOTENTE.
Se ejecuta con el rol propietario del ETL (lp), NO con lp_agent."""
from __future__ import annotations


def ingest_orders(conn, orders: list[dict]) -> int:
    """Upsert idempotente de pedidos del lab en ods.lab_order (DDL en sql/12_lab_ingest.sql).
    Parametrizado (%s), commit al final y rollback ante cualquier fallo. Devuelve cuántas filas procesó."""
    sql = (
        "INSERT INTO ods.lab_order (code, lab_id, customer, dest_x, dest_y, status, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (code) DO UPDATE SET lab_id = EXCLUDED.lab_id, customer = EXCLUDED.customer, "
        "dest_x = EXCLUDED.dest_x, dest_y = EXCLUDED.dest_y, status = EXCLUDED.status, "
        "created_at = EXCLUDED.created_at, ingested_at = now()"
    )
    try:
        with conn.cursor() as cur:
            for o in orders:
                cur.execute(sql, (o["code"], o["id"], o["customer"], o["destX"], o["destY"], o["status"], o["createdAt"]))
        conn.commit()
        return len(orders)
    except Exception:
        conn.rollback()
        raise


def fetch_orders(lab_url: str | None = None) -> list[dict]:
    """Lee todos los pedidos del lab (paginado). Dado."""
    from lpagent.labclient import LabClient

    c, page, out = LabClient(lab_url), 0, []
    while True:
        res = c.get(f"/api/orders?page={page}&size=100")
        out.extend(res["content"])
        page += 1
        if page >= res["totalPages"]:
            return out
