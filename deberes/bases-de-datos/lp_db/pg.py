"""Conexión a Postgres del lakehouse. Variables: PGHOST, PGPORT, PGDATABASE, PGUSER, PGPASSWORD."""
from __future__ import annotations

import os


def connect(user: str | None = None, password: str | None = None):
    import psycopg2  # import perezoso: las pruebas usan una conexión falsa
    return psycopg2.connect(
        host=os.getenv("PGHOST", "localhost"), port=os.getenv("PGPORT", "5432"),
        dbname=os.getenv("PGDATABASE", "logistpulse"),
        user=user or os.getenv("PGUSER", "lp_agent"), password=password or os.getenv("PGPASSWORD", "lp_agent"),
        connect_timeout=3)
