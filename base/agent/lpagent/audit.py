"""Registro de auditoría: cada decisión del agente queda en un sumidero (JSONL por defecto).
El deber de Bases de Datos añade un sumidero Postgres (esquema agent) sin cambiar el agente."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Protocol


class Sink(Protocol):
    def write(self, event: dict) -> None: ...


class JsonlSink:
    def __init__(self, path: str | None = None):
        self.path = path or os.getenv("LP_AUDIT_FILE", "audit.jsonl")
        self._lock = threading.Lock()

    def write(self, event: dict) -> None:
        with self._lock, open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


class MemorySink:
    def __init__(self):
        self.events: list[dict] = []

    def write(self, event: dict) -> None:
        self.events.append(event)


class Audit:
    def __init__(self, *sinks: Sink):
        self.sinks = list(sinks)

    def log(self, kind: str, **data) -> dict:
        ev = {"ts": datetime.now(timezone.utc).isoformat(), "kind": kind, **data}
        for s in self.sinks:
            try:
                s.write(ev)
            except Exception as exc:  # un sumidero caído no debe tumbar al agente
                print(f"[audit] sumidero falló: {exc}")
        return ev
