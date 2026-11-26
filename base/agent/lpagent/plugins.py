"""Carga de adaptadores de los deberes. Variable vacía = adaptador base. Variable con error = fallo explícito."""
from __future__ import annotations

import importlib
import os


def load(env_var: str, default_factory):
    spec = os.getenv(env_var, "").strip()
    if not spec:
        return default_factory()
    mod_name, _, func = spec.partition(":")
    if not func:
        raise ValueError(f"{env_var} debe tener la forma 'modulo:funcion', recibido {spec!r}")
    return getattr(importlib.import_module(mod_name), func)()
