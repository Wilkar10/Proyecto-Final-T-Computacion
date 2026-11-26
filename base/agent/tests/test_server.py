import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from lpagent import server


@pytest.fixture()
def base_url(tmp_path, monkeypatch):
    monkeypatch.setenv("LP_AUDIT_FILE", str(tmp_path / "audit.jsonl"))
    for k in ("LP_SOLVER_PLUGIN", "LP_DATA_PLUGIN", "LP_ACTUATOR_PLUGIN", "LP_PLANNER", "LP_MODE"):
        monkeypatch.delenv(k, raising=False)
    server.Handler.agent = server.build_agent()
    server.Handler.counters = {k: 0 for k in server.Handler.counters}
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()


def call(url, method="GET", headers=None):
    req = urllib.request.Request(url, method=method, headers=headers or {}, data=b"" if method == "POST" else None)
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read() or b"null") if "json" in r.headers.get("Content-Type", "") else r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_full_flow_over_http(base_url, tmp_path):
    assert call(base_url + "/health") == (200, {"status": "UP"})
    st, prop = call(base_url + "/plan", "POST")
    assert st == 201 and prop["status"] == "PENDING_APPROVAL"
    pid = prop["proposal_id"]
    assert call(f"{base_url}/proposals/{pid}/approve", "POST")[0] == 401          # sin X-Approver
    st, done = call(f"{base_url}/proposals/{pid}/approve", "POST", {"X-Approver": "maria"})
    assert st == 200 and done["status"] == "EXECUTED" and done["detail"]["mode"] == "dry-run"
    assert call(f"{base_url}/proposals/{pid}/reject", "POST", {"X-Approver": "maria"})[0] == 409
    st, metrics = call(base_url + "/metrics")
    assert "logistpulse_agent_proposals_total 1" in metrics and "logistpulse_agent_approved_total 1" in metrics
    lines = (tmp_path / "audit.jsonl").read_text().splitlines()
    assert any(json.loads(l)["kind"] == "executed" for l in lines)


def test_unknown_routes(base_url):
    assert call(base_url + "/nada")[0] == 404
    assert call(base_url + "/proposals/zzz/approve", "POST", {"X-Approver": "a"})[0] == 404


def test_audit_plugin_sink_receives_events(tmp_path, monkeypatch):
    """LP_AUDIT_PLUGIN permite que un deber añada un sumidero (p. ej. Postgres) sin tocar el agente."""
    import sys
    import types

    mod = types.ModuleType("fake_sink_mod")
    mod.events = []
    mod.build_sink = lambda: types.SimpleNamespace(write=mod.events.append)
    sys.modules["fake_sink_mod"] = mod
    monkeypatch.setenv("LP_AUDIT_FILE", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("LP_AUDIT_PLUGIN", "fake_sink_mod:build_sink")
    for k in ("LP_SOLVER_PLUGIN", "LP_DATA_PLUGIN", "LP_ACTUATOR_PLUGIN", "LP_PLANNER", "LP_MODE"):
        monkeypatch.delenv(k, raising=False)
    agent = server.build_agent()
    agent.plan()
    assert "proposal_created" in [e["kind"] for e in mod.events]
