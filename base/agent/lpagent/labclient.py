"""Cliente HTTP mínimo (stdlib) hacia la API del lab. Timeout corto y errores explícitos."""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request


class LabError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status


class LabClient:
    def __init__(self, base_url: str | None = None, timeout: float = 3.0):
        self.base = (base_url or os.getenv("LAB_URL", "http://localhost:8080")).rstrip("/")
        if urllib.parse.urlparse(self.base).scheme not in ("http", "https"):
            raise ValueError("LAB_URL debe ser http:// o https:// (no se admiten file:// ni otros esquemas)")
        self.timeout = timeout
        # En modo docker el lab exige X-Api-Key. El agente ESCRIBE (POST /api/trips), así que necesita una clave con permiso write.
        self.api_key = os.getenv("LAB_API_KEY", "")

    def _call(self, method: str, path: str, body: dict | None = None, headers: dict | None = None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={"Content-Type": "application/json", "Accept": "application/json",
                                              **({"X-Api-Key": self.api_key} if self.api_key else {}), **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:  # nosec B310 - esquema validado en __init__
                raw = r.read()
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            try:
                msg = json.loads(e.read()).get("error", e.reason)
            except Exception:
                msg = e.reason
            raise LabError(e.code, str(msg)) from None
        except urllib.error.URLError as e:
            raise LabError(0, f"lab no disponible: {e.reason}") from None

    def get(self, path: str):
        return self._call("GET", path)

    def post(self, path: str, body: dict | None = None, headers: dict | None = None):
        return self._call("POST", path, body, headers)
