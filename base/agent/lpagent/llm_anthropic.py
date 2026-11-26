"""Adaptador OPCIONAL a la API de Anthropic (pip install anthropic). NO se probó contra la API real en esta entrega:
las pruebas del bucle usan un cliente falso. Requiere ANTHROPIC_API_KEY y LP_LLM_MODEL (el id del modelo que elijan)."""
from __future__ import annotations

import os


class AnthropicClient:
    def __init__(self, model: str | None = None, max_tokens: int = 1024):
        import anthropic  # import perezoso: el resto del agente no depende del SDK
        self.model = model or os.environ["LP_LLM_MODEL"]
        self.max_tokens = max_tokens
        self._c = anthropic.Anthropic()

    def complete(self, system: str, messages: list[dict], tools: list[dict]) -> list[dict]:
        resp = self._c.messages.create(model=self.model, max_tokens=self.max_tokens, system=system,
                                       messages=messages, tools=tools)
        out: list[dict] = []
        for b in resp.content:
            if b.type == "text":
                out.append({"type": "text", "text": b.text})
            elif b.type == "tool_use":
                out.append({"type": "tool_use", "id": b.id, "name": b.name, "input": dict(b.input)})
        return out
