"""DECORATOR — capacidades transversales del actuador (reintentos, auditoría) apiladas sin tocar al actuador real.
Todos cumplen ActuatorPort, así que el agente no sabe cuántas capas hay. EL ORDEN IMPORTA (ver PATRONES.md)."""
from __future__ import annotations

import time

from lpagent.audit import Audit


class ActuatorDecorator:
    def __init__(self, inner):
        self.inner = inner

    def execute(self, proposal):
        return self.inner.execute(proposal)


class RetryingActuator(ActuatorDecorator):
    """Reintenta SOLO fallos transitorios. Seguro únicamente si la operación es idempotente (Idempotency-Key)."""

    def __init__(self, inner, retries: int = 2, sleep=time.sleep, transient=lambda exc: getattr(exc, "status", 0) in (0, 502, 503, 504)):
        super().__init__(inner)
        self.retries, self._sleep, self._transient = retries, sleep, transient

    def execute(self, proposal):
        for attempt in range(self.retries + 1):
            try:
                return self.inner.execute(proposal)
            except Exception as exc:
                if attempt == self.retries or not self._transient(exc):
                    raise
                self._sleep(0.5 * (attempt + 1))


class AuditedActuator(ActuatorDecorator):
    """Deja constancia de cada intento de ejecución (incluidos los fallos), con duración."""

    def __init__(self, inner, audit: Audit):
        super().__init__(inner)
        self.audit = audit

    def execute(self, proposal):
        t0 = time.monotonic()
        try:
            result = self.inner.execute(proposal)
        except Exception as exc:
            self.audit.log("actuator_attempt", proposal_id=proposal.proposal_id, ok=False, error=repr(exc),
                           ms=round(1000 * (time.monotonic() - t0)))
            raise
        self.audit.log("actuator_attempt", proposal_id=proposal.proposal_id, ok=True, ms=round(1000 * (time.monotonic() - t0)))
        return result
