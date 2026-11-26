"""Pruebas de contrato. Corren sin Docker: validan los archivos y, además, el agente REAL contra su OpenAPI."""
import copy
import json
import os
import shutil
import sys
import threading
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft7Validator

C = Path(__file__).resolve().parents[1]
REPO = C.parent
sys.path.insert(0, str(C / "tools"))
import validate_contracts as vc  # noqa: E402


def _to_jsonschema(node):
    """OpenAPI 3.0 -> JSON Schema: 'nullable: true' pasa a unión de tipos."""
    if isinstance(node, dict):
        node = {k: _to_jsonschema(v) for k, v in node.items()}
        if node.pop("nullable", False) and "type" in node:
            node["type"] = [node["type"], "null"]
        return node
    if isinstance(node, list):
        return [_to_jsonschema(v) for v in node]
    return node


def test_contratos_validos():
    assert vc.main([]) == 0


def test_catalogo_cubre_los_cuatro_contextos():
    cat = vc.load(C / "catalog.yaml")
    assert {s["name"] for s in cat["services"]} == {"fleet-orders", "inventory-replenishment", "dispatch-decision", "analytics-lakehouse"}
    assert {e["name"] for e in cat["events"]} == {"order.dispatched", "trip.created", "proposal.created", "proposal.decided", "stock.low", "purchase.received", "order.packed"}


@pytest.mark.parametrize("mutar,fragmento", [
    (lambda s: s["properties"].pop("robot"), "se eliminó el campo 'robot'"),
    (lambda s: s["properties"]["cost"].__setitem__("type", "string"), "cambió el tipo"),
    (lambda s: s["required"].append("stopIndex"), "pasó a ser requerido"),
])
def test_detecta_cambios_incompatibles_en_eventos(tmp_path, mutar, fragmento):
    old = vc.load(C / "schemas/trip-created.v1.json")
    new = copy.deepcopy(old)
    if "stopIndex" not in new["properties"]:
        new["properties"]["stopIndex"] = {"type": "integer"}
    mutar(new)
    out = []
    vc.schema_breaks(old, new, "trip-created", out)
    assert any(fragmento in m for m in out), out


def test_campo_opcional_nuevo_es_compatible():
    old = vc.load(C / "schemas/trip-created.v1.json")
    new = copy.deepcopy(old)
    new["properties"]["notes"] = {"type": "string"}
    out = []
    vc.schema_breaks(old, new, "trip-created", out)
    assert out == []


def test_openapi_param_requerido_nuevo_rompe(tmp_path):
    base = tmp_path / "baseline"
    shutil.copytree(C / "baseline", base)
    spec = yaml.safe_load((C / "openapi/fleet-orders.v1.yaml").read_text())
    spec["paths"]["/api/trips"]["post"]["parameters"].append({"name": "X-Tenant", "in": "header", "required": True, "schema": {"type": "string"}})
    errors = []
    work = tmp_path / "work" / "openapi"
    work.mkdir(parents=True)
    old = vc.ROOT
    try:
        (work / "fleet-orders.v1.yaml").write_text(yaml.safe_dump(spec))
        vc.ROOT = tmp_path / "work"
        (vc.ROOT / "schemas").mkdir()
        vc.check_compat(base, errors)
    finally:
        vc.ROOT = old
    assert any("X-Tenant" in e for e in errors)


def test_ejemplo_malo_falla():
    ex = json.loads((C / "examples/trip.created.v1.json").read_text())
    ex["payload"]["cost"] = -1
    errs = list(Draft7Validator(vc.load(C / "schemas/trip-created.v1.json")).iter_errors(ex["payload"]))
    assert errs


def test_no_hay_deriva_entre_contrato_y_codigo():
    """Cada ruta del contrato debe existir en el código que la implementa (anti-deriva básica)."""
    java = "".join(p.read_text() for p in (REPO / "base/lab/src/main/java").rglob("*Resource.java"))
    for path in vc.load(C / "openapi/fleet-orders.v1.yaml")["paths"]:
        first = "/".join(path.split("/")[:3])  # /api/orders
        assert f'@Path("{first}")' in java, f"{first} no está en el lab"
    for path in vc.load(C / "openapi/inventory-replenishment.v1.yaml")["paths"]:
        first = "/".join(path.split("/")[:3])
        assert f'@Path("{first}")' in java, f"{first} no está en el lab"
    srv = (REPO / "base/agent/lpagent/server.py").read_text()
    for path in vc.load(C / "openapi/dispatch-decision.v1.yaml")["paths"]:
        assert path.split("/")[1] in srv, f"{path} no está en el agente"


# ---------- el agente real cumple su contrato ----------
@pytest.fixture()
def agente():
    sys.path[:0] = [str(REPO / "base/agent")]
    for k in ("LP_SOLVER_PLUGIN", "LP_DATA_PLUGIN", "LP_ACTUATOR_PLUGIN", "LP_PLANNER", "LP_MODE", "LP_AUDIT_PLUGIN"):
        os.environ.pop(k, None)
    os.environ["LP_AUDIT_FILE"] = os.devnull
    from lpagent import server
    server.Handler.agent = server.build_agent()
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


def _call(method, url, headers=None):
    req = urllib.request.Request(url, method=method, headers=headers or {}, data=b"" if method == "POST" else None)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_agente_real_cumple_openapi(agente):
    spec = vc.load(C / "openapi/dispatch-decision.v1.yaml")
    schemas = _to_jsonschema(spec["components"]["schemas"])
    proposal = Draft7Validator({"$ref": "#/components/schemas/Proposal", "components": {"schemas": schemas}})
    error = Draft7Validator({"$ref": "#/components/schemas/Error", "components": {"schemas": schemas}})

    st, p = _call("POST", agente + "/plan")
    assert st == 201 and not list(proposal.iter_errors(p)), list(proposal.iter_errors(p))
    pid = p["proposal_id"]
    st, body = _call("POST", f"{agente}/proposals/{pid}/approve")
    assert st == 401 and not list(error.iter_errors(body))
    st, body = _call("POST", f"{agente}/proposals/{pid}/approve", {"X-Approver": "supervisor"})
    assert st == 200 and not list(proposal.iter_errors(body))
    st, body = _call("POST", f"{agente}/proposals/{pid}/approve", {"X-Approver": "supervisor"})
    assert st == 409 and not list(error.iter_errors(body))
    st, body = _call("GET", agente + "/proposals/noexiste")
    assert st == 404 and not list(error.iter_errors(body))
