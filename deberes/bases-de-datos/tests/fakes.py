"""Conexión DB-API falsa: registra (sql, params). Sirve para probar QUÉ se envía, no la semántica del motor."""


class FakeCursor:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql, params=None):
        if self.conn.fail_on and self.conn.fail_on in sql:
            raise RuntimeError("fallo simulado")
        self.conn.executed.append((" ".join(sql.split()), params))

    def fetchone(self):
        return self.conn.rows.pop(0) if self.conn.rows else None

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeConn:
    def __init__(self, rows=None, fail_on=None):
        self.executed, self.rows, self.fail_on = [], list(rows or []), fail_on
        self.commits = self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return FakeCursor(self)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True
