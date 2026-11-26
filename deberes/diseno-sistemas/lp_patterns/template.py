"""TEMPLATE METHOD — el esqueleto del mensaje al aprobador es fijo; cada canal rellena los pasos.
`render` es el método plantilla (no se sobrescribe); header/body son abstractos; footer es un gancho opcional."""
from __future__ import annotations

from abc import ABC, abstractmethod

from lpagent.models import Proposal


class ProposalRenderer(ABC):
    def render(self, p: Proposal) -> str:          # método plantilla: orden invariable
        parts = [self.header(p), *self.body(p)]
        foot = self.footer(p)
        if foot:
            parts.append(foot)
        return "\n".join(parts)

    @abstractmethod
    def header(self, p: Proposal) -> str: ...

    @abstractmethod
    def body(self, p: Proposal) -> list[str]: ...

    def footer(self, p: Proposal) -> str:          # gancho: por defecto no hay pie
        return ""

    @staticmethod
    def battery_use(p: Proposal) -> str:
        return f"{p.cost}/{p.budget} unidades de presupuesto ({100 * p.cost / p.budget:.0f} %)" if p.budget else f"{p.cost}"


class MarkdownRenderer(ProposalRenderer):
    def header(self, p):
        return f"## Propuesta {p.proposal_id} · {p.robot}"

    def body(self, p):
        stops = " → ".join(p.order_codes)
        return [f"- **Recorrido:** origen → {stops} → origen",
                f"- **Costo:** {self.battery_use(p)}",
                f"- **Algoritmo:** {p.algorithm} ({'óptimo' if p.exact else 'heurístico, sin garantía'})",
                f"- **Motivo:** {p.rationale}"]

    def footer(self, p):
        return "_Requiere aprobación humana (POST /proposals/{id}/approve con X-Approver)._"


class PlainRenderer(ProposalRenderer):
    """Canal corto (SMS/chat): sin pie."""

    def header(self, p):
        return f"[{p.proposal_id}] {p.robot}: {len(p.order_codes)} pedidos"

    def body(self, p):
        return [f"costo {p.cost}/{p.budget}; {'óptimo' if p.exact else 'heurístico'}"]
