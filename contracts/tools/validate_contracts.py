"""Validador de contratos LOGISTPULSE (solo PyYAML + jsonschema).

Comprueba: (1) catálogo ↔ archivos, (2) OpenAPI/AsyncAPI bien formados y con $ref resolubles,
(3) ejemplos de eventos válidos contra envelope + schema del payload, (4) compatibilidad contra una línea base.
Uso:  python contracts/tools/validate_contracts.py [--baseline contracts/baseline]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[1]
HTTP = {"get", "post", "put", "patch", "delete"}


def load(p: Path):
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.suffix in (".yaml", ".yml") else json.loads(p.read_text(encoding="utf-8"))


def resolve(doc: dict, ref: str, base: Path):
    """Resuelve $ref local (#/...) o de archivo relativo. Devuelve el nodo o lanza KeyError/FileNotFoundError."""
    file_part, _, frag = ref.partition("#")
    if file_part:
        target = (base.parent / file_part).resolve()
        doc, base = load(target), target
    node = doc
    for part in [p for p in frag.split("/") if p]:
        node = node[part]
    return node


def walk_refs(node):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "$ref" and isinstance(v, str):
                yield v
            else:
                yield from walk_refs(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk_refs(v)


def check_refs(path: Path, errors: list[str]):
    doc = load(path)
    for ref in walk_refs(doc):
        try:
            resolve(doc, ref, path)
        except Exception:  # noqa: BLE001
            errors.append(f"{path.name}: $ref no resoluble {ref}")
    return doc


def check_openapi(path: Path, errors: list[str]):
    doc = check_refs(path, errors)
    if not str(doc.get("openapi", "")).startswith("3."):
        errors.append(f"{path.name}: falta 'openapi: 3.x'")
    ids = []
    for url, item in (doc.get("paths") or {}).items():
        for verb, op in item.items():
            if verb not in HTTP:
                continue
            if "operationId" not in op:
                errors.append(f"{path.name}: {verb.upper()} {url} sin operationId")
            else:
                ids.append(op["operationId"])
            if not op.get("responses"):
                errors.append(f"{path.name}: {verb.upper()} {url} sin responses")
            if verb in ("post", "put", "patch") and "requestBody" not in op and "/approve" not in url and "/reject" not in url and "/receive" not in url and url != "/plan":
                errors.append(f"{path.name}: {verb.upper()} {url} sin requestBody")
    if len(ids) != len(set(ids)):
        errors.append(f"{path.name}: operationId repetido")
    check_api_security(path, doc, errors)
    return doc


def check_api_security(path: Path, doc: dict, errors: list[str]):
    """Política de la capa de API: toda operación declara 401/403/429, su permiso (read/write) y usa el esquema ApiKey."""
    schemes = (doc.get("components") or {}).get("securitySchemes") or {}
    ak = schemes.get("ApiKey")
    if not ak or ak.get("type") != "apiKey" or ak.get("in") != "header" or ak.get("name") != "X-Api-Key":
        errors.append(f"{path.name}: falta securitySchemes.ApiKey (apiKey, header X-Api-Key)")
    if {"ApiKey": []} not in (doc.get("security") or []):
        errors.append(f"{path.name}: falta 'security: [{{ApiKey: []}}]' global")
    if not (doc.get("x-gateway") or {}).get("public_base_path"):
        errors.append(f"{path.name}: falta x-gateway.public_base_path")
    for url, item in (doc.get("paths") or {}).items():
        for verb, op in item.items():
            if verb not in HTTP:
                continue
            where = f"{path.name}: {verb.upper()} {url}"
            for code in ("401", "403", "429"):
                if code not in op.get("responses", {}):
                    errors.append(f"{where} no declara la respuesta {code}")
            want = "read" if verb == "get" else "write"
            if op.get("x-required-scope") != want:
                errors.append(f"{where}: x-required-scope debe ser '{want}' (es {op.get('x-required-scope')!r})")
    resp = (doc.get("components") or {}).get("responses") or {}
    retry = ((resp.get("TooManyRequests") or {}).get("headers") or {})
    if "Retry-After" not in retry:
        errors.append(f"{path.name}: components.responses.TooManyRequests debe declarar el encabezado Retry-After")


def check_asyncapi(path: Path, errors: list[str]):
    doc = check_refs(path, errors)
    if not str(doc.get("asyncapi", "")).startswith("2."):
        errors.append(f"{path.name}: falta 'asyncapi: 2.x'")
    for name, ch in (doc.get("channels") or {}).items():
        if not (ch.get("publish") or ch.get("subscribe")):
            errors.append(f"{path.name}: canal {name} sin publish/subscribe")
    return doc


def check_catalog(errors: list[str]):
    cat = load(ROOT / "catalog.yaml")
    for svc in cat["services"]:
        for api in svc["apis"]:
            if not (ROOT / api["contract"]).exists():
                errors.append(f"catalog: {svc['name']} apunta a {api['contract']} que no existe")
    for ev in cat["events"]:
        if not (ROOT / ev["schema"]).exists():
            errors.append(f"catalog: evento {ev['name']} sin schema {ev['schema']}")
    return cat


def check_examples(cat: dict, errors: list[str]):
    envelope = Draft7Validator(load(ROOT / "schemas/envelope.v1.json"))
    by_name = {e["name"]: e for e in cat["events"]}
    seen = set()
    for f in sorted((ROOT / "examples").glob("*.json")):
        ex = load(f)
        for err in envelope.iter_errors(ex):
            errors.append(f"{f.name}: envelope: {err.message}")
        ev = by_name.get(ex.get("eventType"))
        if not ev:
            errors.append(f"{f.name}: eventType {ex.get('eventType')} no está en el catálogo")
            continue
        seen.add(ev["name"])
        if ex.get("producer") != ev["producer"]:
            errors.append(f"{f.name}: producer {ex.get('producer')} ≠ catálogo {ev['producer']}")
        for err in Draft7Validator(load(ROOT / ev["schema"])).iter_errors(ex.get("payload", {})):
            errors.append(f"{f.name}: payload: {err.message}")
    for name in by_name:
        if name not in seen:
            errors.append(f"catalog: evento {name} no tiene ejemplo en examples/")


# ---------- compatibilidad (rompe / no rompe) ----------
def schema_breaks(old: dict, new: dict, where: str, out: list[str], direction: str = "event"):
    """Para EVENTOS (los consumidores leen): quitar campo, volverlo requerido-ausente o cambiar tipo rompe.
    Un campo nuevo REQUERIDO también rompe a los productores existentes (no lo envían)."""
    op, np_ = old.get("properties", {}), new.get("properties", {})
    for k in op:
        if k not in np_:
            out.append(f"{where}: se eliminó el campo '{k}'")
        elif op[k].get("type") != np_[k].get("type"):
            out.append(f"{where}.{k}: cambió el tipo {op[k].get('type')} → {np_[k].get('type')}")
        elif set(op[k].get("enum", [])) - set(np_[k].get("enum", [])) and "enum" in np_[k]:
            out.append(f"{where}.{k}: se quitaron valores del enum")
    for k in set(new.get("required", [])) - set(old.get("required", [])):
        out.append(f"{where}: el campo '{k}' pasó a ser requerido")


def check_compat(baseline: Path, errors: list[str]):
    for old_f in sorted((baseline / "schemas").glob("*.json")):
        new_f = ROOT / "schemas" / old_f.name
        if not new_f.exists():
            errors.append(f"compat: se eliminó schemas/{old_f.name} (cambio incompatible: crea v2 y mantén v1)")
            continue
        schema_breaks(load(old_f), load(new_f), old_f.name, errors)
    for old_f in sorted((baseline / "openapi").glob("*.yaml")):
        new_f = ROOT / "openapi" / old_f.name
        if not new_f.exists():
            errors.append(f"compat: se eliminó openapi/{old_f.name}")
            continue
        o, n = load(old_f), load(new_f)
        for url, item in o["paths"].items():
            for verb, op in item.items():
                if verb not in HTTP:
                    continue
                nop = ((n["paths"].get(url) or {}).get(verb))
                if nop is None:
                    errors.append(f"compat: {old_f.name} se eliminó {verb.upper()} {url}")
                    continue
                oldreq = {(p["name"], p["in"]) for p in op.get("parameters", []) if p.get("required")}
                for p in nop.get("parameters", []):
                    if p.get("required") and (p["name"], p["in"]) not in oldreq:
                        errors.append(f"compat: {old_f.name} {verb.upper()} {url}: parámetro nuevo REQUERIDO '{p['name']}'")
                for code in op.get("responses", {}):
                    if code not in nop.get("responses", {}):
                        errors.append(f"compat: {old_f.name} {verb.upper()} {url}: se eliminó la respuesta {code}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", default=str(ROOT / "baseline"))
    a = ap.parse_args(argv)
    errors: list[str] = []
    cat = check_catalog(errors)
    for f in sorted((ROOT / "openapi").glob("*.yaml")):
        check_openapi(f, errors)
    for f in sorted((ROOT / "asyncapi").glob("*.yaml")):
        check_asyncapi(f, errors)
    check_examples(cat, errors)
    if Path(a.baseline).exists():
        check_compat(Path(a.baseline), errors)
    for e in errors:
        print("ERROR", e)
    print("contratos OK" if not errors else f"{len(errors)} error(es)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
