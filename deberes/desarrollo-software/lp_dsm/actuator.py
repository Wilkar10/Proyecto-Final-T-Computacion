"""Actuador del agente: ejecuta una propuesta APROBADA llamando a POST /api/trips del lab (contrato en api/trips.openapi.yaml).
Se activa con LP_ACTUATOR_PLUGIN=lp_dsm.actuator:build (y LP_EXECUTE=1 si se usa el compose)."""
from __future__ import annotations


class TripActuator:
    """Despacha un viaje multi-parada de forma atómica e idempotente.
    Comportamiento (lo verifican tests/test_actuator.py):
      1. Un único POST a /api/trips con cuerpo {"robot": <código>, "orders": [<códigos EN EL ORDEN del recorrido>]}.
      2. Cabecera Idempotency-Key = proposal_id (aprobar dos veces NO despacha dos veces).
      3. Reintentos (máx. 2, con espera creciente) SOLO ante errores 5xx o de red (status 0); nunca ante 4xx.
      4. Un 4xx/5xx final se propaga (el agente marca la propuesta como FAILED); no se traga el error.
      5. Devuelve {"mode": "trip", "response": <cuerpo de la respuesta>}."""

    def __init__(self, client=None, sleep=None):
        from lpagent.labclient import LabClient
        import time

        self.client = client or LabClient()
        self._sleep = sleep or time.sleep

    def execute(self, proposal) -> dict:
        from lpagent.labclient import LabError
        body = {"robot": proposal.robot, "orders": list(proposal.order_codes)}
        headers = {"Idempotency-Key": proposal.proposal_id}
        for attempt in range(3):
            try:
                return {"mode": "trip", "response": self.client.post("/api/trips", body, headers)}
            except LabError as e:
                if e.status and e.status < 500 or attempt == 2:
                    raise
                self._sleep(0.5 * (attempt + 1))


def build():
    return TripActuator()
