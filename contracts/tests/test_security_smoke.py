"""La prueba de humo de seguridad se prueba contra un servidor FALSO que cumple (o rompe a propósito) el contrato.
Así sabemos que el script detecta de verdad un 429 ausente, un Retry-After faltante o un permiso mal aplicado,
antes de apuntarlo al stack real (que solo existe en GitHub Actions / la máquina del estudiante)."""
import json
import sys
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

C = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(C / "tools"))
import security_smoke as smoke  # noqa: E402

KEYS = {"lab-dev-dispatcher-key": ("dispatcher", {"read", "write"}), "lab-dev-viewer-key": ("viewer", {"read"})}


class Bucket:
    def __init__(self, cap, rate):
        self.cap, self.rate, self.tokens, self.t, self.lock = cap, rate, cap, time.monotonic(), threading.Lock()

    def take(self):
        with self.lock:
            now = time.monotonic()
            self.tokens = min(self.cap, self.tokens + (now - self.t) * self.rate)
            self.t = now
            if self.tokens >= 1:
                self.tokens -= 1
                return True, 0
            return False, max(1, int((1 - self.tokens) / self.rate) + 1)


def make_server(prefix, *, burst=20, rate=10, bug=None):
    buckets = {}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, status, body, extra=None, rid=None):
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("X-Request-Id", rid)
            for k, v in (extra or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(data)

        def _handle(self, method):
            if method == "POST":
                n = int(self.headers.get("Content-Length") or 0)
                if n:
                    self.rfile.read(n)
            rid = self.headers.get("X-Request-Id", "")
            import re
            if not re.fullmatch(r"[A-Za-z0-9._-]{8,64}", rid):
                rid = str(uuid.uuid4())
            key = self.headers.get("X-Api-Key")
            who = KEYS.get(key)
            client = who[0] if who else "anon"
            if bug != "no_429":
                ok, wait = buckets.setdefault(client, Bucket(burst, rate)).take()
                if not ok:
                    extra = {} if bug == "no_retry_after" else {"Retry-After": str(wait)}
                    return self._send(429, {"status": 429, "error": "Demasiadas solicitudes", "code": "RATE_LIMITED"}, extra, rid)
            if not who:
                body = {"status": 401, "error": "Falta clave", "code": "UNAUTHORIZED"}
                if bug == "leak":
                    body["error"] = "java.lang.NullPointerException at com.logistpulse.lab.api.X"
                return self._send(401, body, None, rid)
            need = "read" if method == "GET" else "write"
            if need not in who[1] and bug != "viewer_can_write":
                return self._send(403, {"status": 403, "error": "sin permiso", "code": "FORBIDDEN"}, None, rid)
            return self._send(200, [], None, rid)

        def do_GET(self):
            self._handle("GET")

        def do_POST(self):
            self._handle("POST")

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def run(bug=None):
    srv, base = make_server("/api", bug=bug)
    try:
        return smoke.main(["--service", base, "--requests", "50"])
    finally:
        srv.shutdown()


def test_el_script_pasa_contra_un_servidor_que_cumple_el_contrato():
    assert run() == 0


@pytest.mark.parametrize("bug", ["no_429", "no_retry_after", "viewer_can_write", "leak"])
def test_el_script_detecta_cada_incumplimiento(bug):
    assert run(bug) == 1


def test_exige_al_menos_un_objetivo():
    with pytest.raises(SystemExit):
        smoke.main([])
