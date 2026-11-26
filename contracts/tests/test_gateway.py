"""El gateway (Kong), el lab (Java) y los contratos describen la MISMA política. Estas pruebas detectan el desvío
cuando alguien cambia una sola de las tres piezas (p. ej. sube el límite en el código y no en kong.yml)."""
import re
from pathlib import Path

import pytest
import yaml

C = Path(__file__).resolve().parents[1]
REPO = C.parent
KONG = yaml.safe_load((REPO / "base/gateway/kong.yml").read_text(encoding="utf-8"))
CAT = yaml.safe_load((C / "catalog.yaml").read_text(encoding="utf-8"))
COMPOSE = yaml.safe_load((REPO / "docker-compose.yml").read_text(encoding="utf-8"))
LAB = REPO / "base/lab/src/main"
READ, WRITE = {"GET", "HEAD", "OPTIONS"}, {"POST", "PUT", "PATCH", "DELETE"}


def props(path: Path) -> dict:
    out = {}
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip() and not ln.lstrip().startswith("#") and "=" in ln:
            k, v = ln.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def default_of(value: str) -> str:
    """'${VAR:valor}' -> 'valor'  (el default de un placeholder de Spring)."""
    m = re.fullmatch(r"\$\{[A-Z_]+:(.*)\}", value)
    return m.group(1) if m else value


def svc(name):
    return next(s for s in KONG["services"] if s["name"] == name)


def plugin(owner, name):
    return next(p for p in owner.get("plugins", []) if p["name"] == name)


def test_los_servicios_del_gateway_son_los_del_catalogo():
    """Cada contrato OpenAPI del catálogo se publica por algún servicio de Kong (gateway_service si comparte upstream)."""
    cat = {}
    for s in CAT["services"]:
        api = next((a for a in s["apis"] if a["kind"] == "openapi"), None)
        if api:
            cat.setdefault(s.get("gateway_service", s["name"]), []).append(api)
    assert {s["name"] for s in KONG["services"]} == set(cat)
    for name, apis in cat.items():
        for api in apis:
            assert {r["paths"][0] for r in svc(name)["routes"]} == {api["public_base_path"]}, name


def test_el_contrato_de_inventario_comparte_ruta_clave_y_limite_con_fleet_orders():
    inv = next(s for s in CAT["services"] if s["name"] == "inventory-replenishment")
    fleet = next(s for s in CAT["services"] if s["name"] == "fleet-orders")
    assert inv["gateway_service"] == "fleet-orders" and inv["implementation"] == fleet["implementation"]


def test_el_destino_de_cada_servicio_existe_en_compose_y_respeta_el_base_path():
    for s in KONG["services"]:
        host = re.match(r"https?://([^:/]+)", s["url"]).group(1)
        service_names = set(COMPOSE["services"]) | {"api"}      # 'api' viene del compose incluido del lab
        assert host in service_names, f"{s['name']} apunta a '{host}', que no es un servicio de compose"
    api = next(a for sv in CAT["services"] for a in sv["apis"] if a["kind"] == "openapi" and sv["name"] == "fleet-orders")
    assert svc("fleet-orders")["url"].endswith(api["base_path"])


@pytest.mark.parametrize("name", ["fleet-orders", "dispatch-decision"])
def test_cada_metodo_http_tiene_exactamente_una_ruta_con_el_permiso_correcto(name):
    routes = svc(name)["routes"]
    covered = {}
    for r in routes:
        allow = next(p for p in r["plugins"] if p["name"] == "acl")["config"]["allow"]
        for m in r["methods"]:
            assert m not in covered, f"{name}: {m} está en dos rutas"
            covered[m] = allow
    for m in READ:
        assert covered[m] == ["read"], f"{name}: {m} debe exigir solo 'read'"
    for m in WRITE:
        assert covered[m] == ["write"], f"{name}: {m} debe exigir 'write'"


def test_los_permisos_del_openapi_coinciden_con_las_rutas_del_gateway():
    for f in (C / "openapi").glob("*.yaml"):
        doc = yaml.safe_load(f.read_text(encoding="utf-8"))
        for url, item in doc["paths"].items():
            for verb, op in item.items():
                if verb in ("get", "post", "put", "patch", "delete"):
                    want = "read" if verb.upper() in READ else "write"
                    assert op["x-required-scope"] == want, f"{f.name} {verb} {url}"


def test_las_claves_del_gateway_son_las_del_lab_en_modo_docker():
    spec = default_of(props(LAB / "resources/application-docker.properties")["lab.security.api-keys"])
    lab = {}
    for item in spec.split(";"):
        name, key, scopes = item.split(":")
        lab[name] = (key, set(scopes.split(",")))
    kong = {}
    for c in KONG["consumers"]:
        kong[c["username"]] = (c["keyauth_credentials"][0]["key"], {a["group"] for a in c["acls"]})
    assert kong == lab


def test_el_limite_de_tasa_es_el_mismo_en_kong_codigo_y_catalogo():
    rl = CAT["gateway"]["rate_limit"]
    for s in KONG["services"]:
        cfg = plugin(s, "rate-limiting")["config"]
        assert cfg["second"] == rl["refill_per_second"], s["name"]
        assert cfg["limit_by"] == "consumer" and cfg["error_code"] == rl["status"] == 429
    base = props(LAB / "resources/application.properties")
    docker = props(LAB / "resources/application-docker.properties")
    assert int(base["lab.security.rate-limit.burst"]) == rl["burst"]
    assert float(base["lab.security.rate-limit.refill-per-second"]) == rl["refill_per_second"]
    assert int(default_of(docker["lab.security.rate-limit.burst"])) == rl["burst"]
    assert float(default_of(docker["lab.security.rate-limit.refill-per-second"])) == rl["refill_per_second"]


def test_cabeceras_de_seguridad_y_correlacion_coinciden_con_el_catalogo():
    for s in KONG["services"]:
        assert plugin(s, "key-auth")["config"]["key_names"] == [CAT["gateway"]["auth"]["header"]]
        assert plugin(s, "key-auth")["config"]["key_in_query"] is False      # la clave nunca en la URL (se filtra a logs)
    corr = plugin(KONG, "correlation-id")["config"]
    assert corr["header_name"] == CAT["gateway"]["correlation_header"] and corr["echo_downstream"] is True


def test_el_gateway_no_publica_la_admin_api_y_monta_la_configuracion_en_solo_lectura():
    gw = COMPOSE["services"]["gateway"]
    assert gw["ports"] == ["8000:8000"]
    assert gw["environment"]["KONG_ADMIN_LISTEN"].startswith("127.0.0.1")
    assert gw["environment"]["KONG_DATABASE"] == "off"
    assert any(v.endswith("/kong/kong.yml:ro") for v in gw["volumes"])
    assert gw["profiles"] == ["gateway"]


def test_el_lab_registra_los_filtros_en_el_orden_correcto():
    cfg = (LAB / "java/com/logistpulse/lab/api/JerseyConfig.java").read_text(encoding="utf-8")
    for cls in ("RequestIdFilter", "RateLimitFilter", "ApiKeyFilter"):
        assert f"register({cls}.class)" in cfg
    prio = {}
    for cls in ("RequestIdFilter", "RateLimitFilter", "ApiKeyFilter"):
        src = (LAB / f"java/com/logistpulse/lab/security/{cls}.java").read_text(encoding="utf-8")
        prio[cls] = int(re.search(r"@Priority\((\d+)\)", src).group(1))
    # correlación -> límite de tasa (también frena a quien prueba claves) -> autenticación
    assert prio["RequestIdFilter"] < prio["RateLimitFilter"] < prio["ApiKeyFilter"]


def test_la_ui_del_lab_envia_la_clave():
    html = (LAB / "resources/ui/index.html").read_text(encoding="utf-8")
    assert "X-Api-Key" in html and "429" in html
