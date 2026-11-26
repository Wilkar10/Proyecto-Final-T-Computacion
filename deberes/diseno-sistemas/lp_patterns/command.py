"""COMMAND — cada acción del operador es un objeto: se registra, se audita y puede (o no) deshacerse.
Problema: la API HTTP, un CLI y un chat de aprobación deben ejecutar las MISMAS acciones con la misma trazabilidad.
Invocador: CommandBus. Receptor: DispatchAgent."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone


class NotUndoable(Exception):
    """Aprobar/rechazar es una decisión humana auditada: no se revierte (se corrige con otra propuesta)."""


class Command(ABC):
    name = "command"

    @abstractmethod
    def execute(self): ...

    def undo(self):
        raise NotUndoable(f"{self.name} no es reversible")


class PlanCommand(Command):
    name = "plan"

    def __init__(self, agent):
        self.agent, self.proposal = agent, None

    def execute(self):
        self.proposal, why = self.agent.plan()
        return self.proposal, why

    def undo(self):
        """Retirar una propuesta que sigue PENDIENTE (aún nadie decidió). Una ya decidida no se retira."""
        p = self.proposal
        if p is None or p.status != "PENDING_APPROVAL":
            raise NotUndoable("solo se retira una propuesta pendiente")
        self.agent.proposals.pop(p.proposal_id, None)
        self.agent.audit.log("withdrawn", proposal_id=p.proposal_id)


class ApproveCommand(Command):
    name = "approve"

    def __init__(self, agent, proposal_id: str, approver: str):
        self.agent, self.proposal_id, self.approver = agent, proposal_id, approver

    def execute(self):
        return self.agent.decide(self.proposal_id, self.approver, True)


class RejectCommand(ApproveCommand):
    name = "reject"

    def execute(self):
        return self.agent.decide(self.proposal_id, self.approver, False)


@dataclass
class Record:
    command: str
    ok: bool
    at: str
    error: str = ""


class CommandBus:
    """Invocador: ejecuta, registra historial (también los fallos) y apila los comandos reversibles."""

    def __init__(self):
        self.history: list[Record] = []
        self._undo_stack: list[Command] = []

    def run(self, cmd: Command):
        now = datetime.now(timezone.utc).isoformat()
        try:
            result = cmd.execute()
        except Exception as exc:
            self.history.append(Record(cmd.name, False, now, repr(exc)))
            raise
        self.history.append(Record(cmd.name, True, now))
        if isinstance(cmd, PlanCommand) and result[0] is not None:
            self._undo_stack.append(cmd)
        return result

    def undo_last(self):
        if not self._undo_stack:
            raise NotUndoable("no hay nada que deshacer")
        cmd = self._undo_stack.pop()
        cmd.undo()
        self.history.append(Record(f"undo:{cmd.name}", True, datetime.now(timezone.utc).isoformat()))
