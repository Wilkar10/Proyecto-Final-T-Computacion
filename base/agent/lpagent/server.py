"""API HTTP del agente (stdlib). Endpoints:
GET /health · GET /metrics · POST /plan · GET /proposals · GET /proposals/{id}
POST /proposals/{id}/approve|reject  (cabecera X-Approver obligatoria)"""
from __future__ import annotations

import json
import os
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .agent import DispatchAgent
from .audit import Audit, JsonlSink
from .baseline import BaselineSolver, DryRunActuator, FixtureData, LabActuator, LabData
from .plugins import load


def build_agent() -> DispatchAgent:
    mode = os.getenv("LP_MODE", "fixture")  # fixture | lab
    default_data = (lambda: LabData()) if mode == "lab" else (lambda: FixtureData())
    default_act = (lambda: LabActuator()) if (mode == "lab" and os.getenv("LP_EXECUTE", "0") == "1") else (lambda: DryRunActuator())
    data = load("LP_DATA_PLUGIN", default_data)
    solver = load("LP_SOLVER_PLUGIN", BaselineSolver)
    actuator = load("LP_ACTUATOR_PLUGIN", default_act)
    planner = None
    if os.getenv("LP_PLANNER", "rule") == "llm":
        from .llm_anthropic import AnthropicClient
        from .planner import LLMPlanner
        planner = LLMPlanner(AnthropicClient(), solver)
    extra_sink = load("LP_AUDIT_PLUGIN", lambda: None)  # p. ej. lp_db.plugin:build_sink (deber de Bases de Datos)
    sinks = [JsonlSink()] + ([extra_sink] if extra_sink else [])
    return DispatchAgent(data, solver, actuator, Audit(*sinks), planner)


class Handler(BaseHTTPRequestHandler):
    agent: DispatchAgent
    counters = {"plans": 0, "proposals": 0, "approved": 0, "rejected": 0, "no_proposal": 0}
    lock = threading.Lock()

    def _send(self, code: int, body, ctype="application/json"):
        raw = body.encode() if isinstance(body, str) else json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):  # silencioso: la auditoría es el registro
        pass

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "UP"})
        if self.path == "/metrics":
            text = "".join(f"logistpulse_agent_{k}_total {v}\n" for k, v in self.counters.items())
            return self._send(200, text, "text/plain")
        if self.path == "/proposals":
            return self._send(200, [p.__dict__ for p in self.agent.proposals.values()])
        m = re.fullmatch(r"/proposals/(\w+)", self.path)
        if m and m.group(1) in self.agent.proposals:
            return self._send(200, self.agent.proposals[m.group(1)].__dict__)
        self._send(404, {"error": "no encontrado"})

    def do_POST(self):
        if self.path == "/plan":
            with self.lock:
                self.counters["plans"] += 1
                proposal, reason = self.agent.plan()
                if proposal is None:
                    self.counters["no_proposal"] += 1
                    return self._send(409, {"error": reason})
                self.counters["proposals"] += 1
            return self._send(201, proposal.__dict__)
        m = re.fullmatch(r"/proposals/(\w+)/(approve|reject)", self.path)
        if m:
            approver = self.headers.get("X-Approver", "")
            try:
                p = self.agent.decide(m.group(1), approver, m.group(2) == "approve")
            except PermissionError as e:
                return self._send(401, {"error": str(e)})
            except KeyError:
                return self._send(404, {"error": "propuesta inexistente"})
            except ValueError as e:
                return self._send(409, {"error": str(e)})
            self.counters["approved" if m.group(2) == "approve" else "rejected"] += 1
            return self._send(200, p.__dict__)
        self._send(404, {"error": "no encontrado"})


def main():
    Handler.agent = build_agent()
    port = int(os.getenv("PORT", "8090"))
    print(f"lpagent escuchando en {os.getenv('LP_BIND', '127.0.0.1')}:{port} (modo={os.getenv('LP_MODE', 'fixture')})")
    # Por defecto SOLO localhost; el contenedor lo abre con LP_BIND=0.0.0.0 (Dockerfile). Abrirlo en un portátil expone el agente a la red.
    host = os.getenv("LP_BIND", "127.0.0.1")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
