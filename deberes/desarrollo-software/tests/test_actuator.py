"""Tarea S3 (roja hasta implementar TripActuator.execute)."""
import pytest
from lpagent.labclient import LabError
from lpagent.models import Proposal

from lp_dsm.actuator import TripActuator



def proposal():
    return Proposal(proposal_id="abc123", robot="AMR-01", order_codes=["LP-DEMO05", "LP-DEMO01"], cost=30, budget=80,
                    battery_before=100, algorithm="brute_force", exact=True, rationale="r")


class FakeClient:
    def __init__(self, errors=()):
        self.errors, self.calls = list(errors), []

    def post(self, path, body=None, headers=None):
        self.calls.append((path, body, headers))
        if self.errors:
            raise self.errors.pop(0)
        return {"tripId": 7, "status": "DISPATCHED"}


def make(errors=()):
    c = FakeClient(errors)
    sleeps = []
    return TripActuator(c, sleep=sleeps.append), c, sleeps


def test_single_post_with_ordered_orders_and_idempotency_key():
    act, c, _ = make()
    out = act.execute(proposal())
    assert len(c.calls) == 1
    path, body, headers = c.calls[0]
    assert path == "/api/trips" and body == {"robot": "AMR-01", "orders": ["LP-DEMO05", "LP-DEMO01"]}
    assert headers["Idempotency-Key"] == "abc123"
    assert out == {"mode": "trip", "response": {"tripId": 7, "status": "DISPATCHED"}}


def test_retries_5xx_and_network_errors_with_growing_wait():
    act, c, sleeps = make([LabError(503, "x"), LabError(0, "red")])
    assert act.execute(proposal())["mode"] == "trip"
    assert len(c.calls) == 3 and len(sleeps) == 2 and sleeps[1] > sleeps[0] > 0


def test_gives_up_after_two_retries_and_propagates():
    act, c, _ = make([LabError(500, "a"), LabError(500, "b"), LabError(500, "c")])
    with pytest.raises(LabError):
        act.execute(proposal())
    assert len(c.calls) == 3


@pytest.mark.parametrize("status", [400, 404, 409, 422])
def test_never_retries_client_errors(status):
    act, c, sleeps = make([LabError(status, "no")])
    with pytest.raises(LabError):
        act.execute(proposal())
    assert len(c.calls) == 1 and not sleeps
