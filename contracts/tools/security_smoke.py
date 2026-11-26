#!/usr/bin/env python3
"""Prueba de humo de SEGURIDAD de la capa de API (solo biblioteca estándar).

Se ejecuta contra el stack VIVO (gateway :8000 y/o lab :8080) y comprueba el contrato de seguridad:
  401 sin clave o con clave falsa · 403 con clave sin permiso · 429 + Retry-After al exceder la ráfaga ·
  X-Request-Id de ida y vuelta · errores JSON sin trazas internas · recuperación tras esperar Retry-After.

Uso:
  python3 contracts/tools/security_smoke.py --gateway http://localhost:8000 --service http://localhost:8080
Salida 0 si todo cumple; 1 si algo falla. La usa el pipeline DAST (.github/workflows/ci-seguridad-dast.yml).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

LEAK = re.compile(r"(Exception|\bat [a-z]+\.[a-z]+\.|java\.lang|org\.springframework|Traceback|stack ?trace)", re.I)


def call(method: str, url: str, headers: dict | None = None, body: bytes | None = None, timeout: float = 10.0):
    if urllib.parse.urlparse(url).scheme not in ("http", "https"):
        raise ValueError(f"esquema no permitido: {url}")
    req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec B310 - esquema validado arriba
            return r.status, {k.lower(): v for k, v in r.headers.items()}, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, {k.lower(): v for k, v in e.headers.items()}, e.read().decode("utf-8", "replace")


class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[bool, str]] = []

    def check(self, ok: bool, what: str, detail: str = "") -> bool:
        self.rows.append((ok, what + (f" — {detail}" if detail and not ok else "")))
        print(("  ok    " if ok else "  FALLO ") + self.rows[-1][1])
        return ok

    @property
    def failed(self) -> int:
        return sum(1 for ok, _ in self.rows if not ok)


def burst(url: str, headers: dict, n: int, workers: int = 8):
    """n peticiones GET lo más rápido posible. Devuelve [(status, headers, body)]."""
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(lambda _: call("GET", url, headers), range(n)))


def check_target(rep: Report, label: str, base: str, prefix: str, keys: dict, *, burst_limit: int, refill: float,
                 requests: int) -> None:
    """prefix: '/api/v1' (gateway) o '/api' (servicio directo)."""
    print(f"\n== {label}: {base}{prefix}")
    orders, robots, trips = f"{base}{prefix}/orders", f"{base}{prefix}/robots", f"{base}{prefix}/trips"
    dispatcher, viewer = {"X-Api-Key": keys["dispatcher"]}, {"X-Api-Key": keys["viewer"]}

    s, h, b = call("GET", orders)
    rep.check(s == 401, f"{label}: sin clave => 401", f"obtuvo {s}")
    rep.check(not LEAK.search(b), f"{label}: el 401 no filtra trazas internas", b[:120])

    s, h, b = call("GET", orders, {"X-Api-Key": "clave-falsa-0123456789"})
    rep.check(s == 401, f"{label}: clave falsa => 401", f"obtuvo {s}")

    s, h, b = call("GET", robots, viewer)
    rep.check(s == 200, f"{label}: viewer puede LEER (read) => 200", f"obtuvo {s}")

    s, h, b = call("POST", trips, {**viewer, "Content-Type": "application/json", "Idempotency-Key": "smoke-viewer-0001"},
                   b'{"robot":"AMR-01","orders":["LP-X"]}')
    rep.check(s == 403, f"{label}: viewer NO puede escribir (write) => 403", f"obtuvo {s}")

    s, h, b = call("GET", robots, {**dispatcher, "X-Request-Id": "smoke-req-12345678"})
    rep.check(s == 200, f"{label}: dispatcher lee => 200", f"obtuvo {s}")
    rep.check(h.get("x-request-id") == "smoke-req-12345678", f"{label}: X-Request-Id seguro vuelve igual",
              f"recibió {h.get('x-request-id')!r}")

    s, h, b = call("GET", robots, {**dispatcher, "X-Request-Id": "mal id con espacios!"})
    rid = h.get("x-request-id", "")
    rep.check(s == 200 and rid != "mal id con espacios!" and re.fullmatch(r"[0-9a-fA-F-]{36}|[\w.-]{8,64}", rid or "") is not None,
              f"{label}: X-Request-Id inseguro se reemplaza", f"recibió {rid!r}")

    # --- ráfaga (al final: vacía la cubeta del dispatcher) ---
    t0 = time.monotonic()
    res = burst(robots, dispatcher, requests)
    elapsed = time.monotonic() - t0
    ok = sum(1 for r in res if r[0] == 200)
    limited = [r for r in res if r[0] == 429]
    # techo teórico de peticiones permitidas: ráfaga + recarga durante el tiempo que duró la ráfaga (+ margen de 2)
    ceiling = burst_limit + refill * elapsed + 2
    rep.check(len(limited) >= 1, f"{label}: al exceder la ráfaga aparece 429 ({len(limited)} de {requests})",
              f"estados: {sorted({r[0] for r in res})}")
    rep.check(ok <= ceiling, f"{label}: no pasan más de ráfaga+recarga ({ok} ≤ {ceiling:.0f})", f"pasaron {ok}")
    if limited:
        ra = [r[1].get("retry-after") for r in limited]
        rep.check(all(x is not None and x.isdigit() and int(x) >= 1 for x in ra),
                  f"{label}: todo 429 trae Retry-After >= 1", f"valores: {sorted(set(map(str, ra)))}")
        rep.check(all(not LEAK.search(r[2]) for r in limited), f"{label}: el 429 no filtra trazas internas")
        wait = max([int(x) for x in ra if x and x.isdigit()] or [1])
        time.sleep(min(wait, 5) + 0.5)
        s, h, b = call("GET", robots, dispatcher)
        rep.check(s == 200, f"{label}: tras esperar Retry-After se recupera => 200", f"obtuvo {s}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gateway", help="URL del gateway, p. ej. http://localhost:8000")
    ap.add_argument("--service", help="URL del lab directo, p. ej. http://localhost:8080")
    ap.add_argument("--dispatcher-key", default="lab-dev-dispatcher-key")
    ap.add_argument("--viewer-key", default="lab-dev-viewer-key")
    ap.add_argument("--burst", type=int, default=20, help="ráfaga configurada (por defecto 20)")
    ap.add_argument("--refill", type=float, default=10, help="fichas por segundo configuradas (por defecto 10)")
    ap.add_argument("--requests", type=int, default=60, help="peticiones de la ráfaga de prueba")
    a = ap.parse_args(argv)
    if not (a.gateway or a.service):
        ap.error("indica --gateway y/o --service")
    keys = {"dispatcher": a.dispatcher_key, "viewer": a.viewer_key}
    rep = Report()
    if a.service:
        # el servicio directo usa token bucket (ráfaga 20, 10/s)
        check_target(rep, "servicio", a.service.rstrip("/"), "/api", keys, burst_limit=a.burst, refill=a.refill,
                     requests=a.requests)
    if a.gateway:
        # el gateway usa ventana fija de 1 s (10 peticiones): en el cambio de ventana pueden pasar hasta 2×10
        check_target(rep, "gateway", a.gateway.rstrip("/"), "/api/v1", keys, burst_limit=int(2 * a.refill), refill=a.refill,
                     requests=a.requests)
    print(f"\n{len(rep.rows) - rep.failed}/{len(rep.rows)} comprobaciones correctas")
    return 1 if rep.failed else 0


if __name__ == "__main__":
    sys.exit(main())
