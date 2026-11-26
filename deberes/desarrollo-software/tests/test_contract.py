"""Pruebas de CONTRATO agente ↔ lab contra el lab VIVO. Se omiten si LAB_URL no está definido o no responde.
   LAB_URL=http://localhost:8080 LAB_API_KEY=lab-dev-dispatcher-key pytest tests/test_contract.py
Extiendan este archivo con el contrato de /api/trips (tarea S2/S3)."""
import json
import os
import urllib.error
import urllib.request

import pytest

LAB = os.getenv("LAB_URL", "").rstrip("/")
KEY = os.getenv("LAB_API_KEY", "")   # el lab en modo docker exige X-Api-Key (clave con permiso write)


def call(method, path, body=None):
    req = urllib.request.Request(LAB + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Content-Type": "application/json", **({"X-Api-Key": KEY} if KEY else {})})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            raw = r.read()
            return r.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"null")


@pytest.fixture(scope="module", autouse=True)
def lab_up():
    if not LAB:
        pytest.skip("LAB_URL no definido")
    try:
        call("GET", "/actuator/health")
    except Exception as exc:  # noqa: BLE001
        pytest.skip(f"lab no disponible: {exc}")


def test_orders_page_shape_used_by_agent():
    st, page = call("GET", "/api/orders?status=CREATED&page=0&size=5")
    assert st == 200 and {"content", "page", "size", "totalElements", "totalPages"} <= set(page)
    for o in page["content"]:
        assert {"id", "code", "customer", "destX", "destY", "status"} <= set(o)


def test_robots_shape_used_by_agent():
    st, robots = call("GET", "/api/robots")
    assert st == 200 and isinstance(robots, list) and robots
    assert {"id", "code", "x", "y", "battery", "status"} <= set(robots[0])


def test_grid_shape_and_default_costs():
    st, g = call("GET", "/api/routes/grid")
    assert st == 200 and all(isinstance(r, str) for r in g["rows"]) and g["width"] == len(g["rows"][0])
    st, r = call("GET", "/api/routes?toX=11&toY=0")
    assert st == 200 and r["cost"] == 11            # mismo valor que el test Java y el Dijkstra del agente
    assert call("GET", "/api/routes?toX=1&toY=1")[0] == 422


def test_agent_loads_live_context():
    from lpagent.baseline import LabData
    from lpagent.labclient import LabClient

    ctx = LabData(LabClient(LAB)).load_context()
    assert ctx.robots and ctx.grid_rows


def test_dispatch_is_not_repeatable():
    st, created = call("POST", "/api/orders", {"customer": "Contrato", "destX": 10, "destY": 5})
    assert st == 201
    assert call("POST", f"/api/orders/{created['id']}/dispatch")[0] == 200
    assert call("POST", f"/api/orders/{created['id']}/dispatch")[0] == 409
