"""Medición empírica con límite de tiempo por llamada (proceso aparte, así un algoritmo exponencial no cuelga todo).
Uso:  python -m np_lab.bench tsp 4 5 6 7 8 9 10   ->  imprime CSV  n,algoritmo,segundos,costo"""
from __future__ import annotations

import multiprocessing as mp
import sys
import time

from . import tsp
from .instances import random_tsp


def _worker(q, fn, args):
    t0 = time.perf_counter()
    try:
        out = fn(*args)
        q.put(("ok", time.perf_counter() - t0, out))
    except Exception as exc:  # noqa: BLE001
        q.put(("error", time.perf_counter() - t0, repr(exc)))


def run_with_timeout(fn, args=(), seconds: float = 10.0):
    """Devuelve (estado, segundos, resultado); estado: ok | timeout | todo | error."""
    ctx = mp.get_context("spawn")
    q = ctx.Queue()
    p = ctx.Process(target=_worker, args=(q, fn, args))
    p.start()
    p.join(seconds)
    if p.is_alive():
        p.terminate()
        p.join()
        return "timeout", seconds, None
    return q.get() if not q.empty() else ("error", 0.0, "sin resultado")


def _cost_of(res):
    return res[1] if isinstance(res, tuple) else None


def bench_tsp(ns, seconds=10.0, seed=1):
    algos = {"brute_force": lambda d: tsp.brute_force(d), "held_karp": lambda d: tsp.held_karp(d),
             "nearest_neighbor": lambda d: (lambda t: (t, tsp.tour_cost(d, t)))(tsp.nearest_neighbor(d))}
    rows = []
    for n in ns:
        d = random_tsp(n, seed)
        for name in algos:
            st, secs, res = run_with_timeout(_run_named, (name, d), seconds)
            rows.append((n, name, st, round(secs, 4), _cost_of(res)))
    return rows


def _run_named(name, d):  # top-level para poder enviarse a otro proceso (spawn)
    if name == "brute_force":
        return tsp.brute_force(d)
    if name == "held_karp":
        return tsp.held_karp(d)
    t = tsp.nearest_neighbor(d)
    return t, tsp.tour_cost(d, t)


def main(argv):
    if len(argv) < 3 or argv[1] != "tsp":
        print(__doc__)
        return 1
    print("n,algoritmo,estado,segundos,costo")
    for row in bench_tsp([int(x) for x in argv[2:]]):
        print(",".join(str(v) for v in row))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
