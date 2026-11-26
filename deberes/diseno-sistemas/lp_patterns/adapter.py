"""ADAPTER — convierte interfaces ajenas al contrato que el agente espera, sin modificar a ninguno de los dos.
1) LabOrderAdapter: DTO JSON del lab -> Stop del dominio.
2) ToolCallsLLMAdapter: proveedor de LLM con formato «tool_calls» -> puerto LLMClient (bloques text/tool_use).
Consecuencia: cambiar de proveedor de IA = escribir otro adaptador; el planificador no cambia."""
from __future__ import annotations

import json
from typing import Callable

from lpagent.models import Stop


class LabOrderAdapter:
    def __init__(self, priority_of: Callable[[str], float]):
        self.priority_of = priority_of

    def to_stop(self, dto: dict) -> Stop:
        return Stop(dto["code"], int(dto["destX"]), int(dto["destY"]), float(self.priority_of(dto.get("customer", ""))))


class ToolCallsLLMAdapter:
    """`call(messages, tools) -> {"message": {"content": str|None, "tool_calls": [{"id","function":{"name","arguments":"{json}"}}]}}`"""

    def __init__(self, call: Callable[[list[dict], list[dict]], dict]):
        self.call = call

    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> list[dict]:
        vendor_tools = [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                                          "parameters": t["input_schema"]}} for t in tools]
        msg = self.call([{"role": "system", "content": system}, *self._to_vendor(messages)], vendor_tools)["message"]
        blocks: list[dict] = []
        if msg.get("content"):
            blocks.append({"type": "text", "text": msg["content"]})
        for tc in msg.get("tool_calls") or []:
            try:
                args = json.loads(tc["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                args = {}   # argumentos corruptos: el validador del planner los rechazará con un error claro
            blocks.append({"type": "tool_use", "id": tc["id"], "name": tc["function"]["name"], "input": args})
        return blocks

    @staticmethod
    def _to_vendor(messages: list[dict]) -> list[dict]:
        out: list[dict] = []
        for m in messages:
            c = m["content"]
            if isinstance(c, str):
                out.append({"role": m["role"], "content": c})
            elif m["role"] == "assistant":
                text = " ".join(b["text"] for b in c if b.get("type") == "text")
                calls = [{"id": b["id"], "type": "function", "function": {"name": b["name"], "arguments": json.dumps(b["input"])}}
                         for b in c if b.get("type") == "tool_use"]
                out.append({"role": "assistant", "content": text or None, **({"tool_calls": calls} if calls else {})})
            else:
                for b in c:
                    if b.get("type") == "tool_result":
                        out.append({"role": "tool", "tool_call_id": b["tool_use_id"], "content": b["content"]})
        return out
