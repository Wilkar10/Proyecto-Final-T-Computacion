"""OBSERVER — el agente publica hechos; métricas, notificaciones y alertas se suscriben sin que el agente los conozca.
Sujeto: ObservableAudit (cada Audit.log es un hecho). Observadores: MetricsObserver, ApproverNotifier."""
from __future__ import annotations

from collections import Counter
from typing import Callable

from lpagent.audit import Audit

Handler = Callable[[dict], None]


class EventBus:
    def __init__(self):
        self._subs: list[tuple[str, Handler]] = []
        self.errors: list[str] = []

    def subscribe(self, kind: str, handler: Handler) -> None:
        """kind concreto (p. ej. 'proposal_created') o '*' para todos."""
        self._subs.append((kind, handler))

    def unsubscribe(self, handler: Handler) -> None:
        self._subs = [(k, h) for k, h in self._subs if h is not handler]

    def publish(self, event: dict) -> None:
        for kind, handler in list(self._subs):
            if kind in ("*", event["kind"]):
                try:
                    handler(event)
                except Exception as exc:  # un observador defectuoso nunca debe afectar al agente ni a los demás
                    self.errors.append(f"{getattr(handler, '__name__', handler)}: {exc!r}")


class ObservableAudit(Audit):
    """Es un Audit (el agente no nota la diferencia: sustitución de Liskov) que además notifica a los suscriptores."""

    def __init__(self, bus: EventBus, *sinks):
        super().__init__(*sinks)
        self.bus = bus

    def log(self, kind: str, **data) -> dict:
        ev = super().log(kind, **data)
        self.bus.publish(ev)
        return ev


class MetricsObserver:
    def __init__(self):
        self.counts: Counter = Counter()

    def __call__(self, event: dict) -> None:
        self.counts[event["kind"]] += 1

    @property
    def acceptance_rate(self) -> float | None:
        decided = self.counts["approved"] + self.counts["rejected"]
        return None if decided == 0 else self.counts["approved"] / decided


class ApproverNotifier:
    """Genera el mensaje para quien aprueba cuando nace una propuesta. `render` es un ProposalRenderer (Template Method)."""

    def __init__(self, render, send: Callable[[str], None] | None = None):
        self.render, self.outbox = render, []
        self.send = send or self.outbox.append

    def __call__(self, event: dict) -> None:
        from lpagent.models import Proposal
        p = Proposal(**{k: v for k, v in event["proposal"].items() if k in Proposal.__dataclass_fields__})
        self.send(self.render.render(p))
