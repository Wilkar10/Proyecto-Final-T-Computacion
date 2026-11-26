"""Calidad del pipeline. Parte BASE (verde): higiene mínima. Parte DEBER (roja hasta que la implementen)."""
import re

import pytest
import yaml
from repo import LAB, ROOT, WORKFLOWS


def workflows():
    return {p.name: yaml.safe_load(p.read_text(encoding="utf-8")) for p in sorted(WORKFLOWS.glob("*.yml"))}


def uses_of(wf):
    for job in wf["jobs"].values():
        for step in job.get("steps", []):
            if "uses" in step:
                yield step["uses"]


# ------------------------------------------------------------------ BASE (verde)
def test_workflows_parse_and_have_jobs():
    wfs = workflows()
    assert wfs, "no hay workflows"
    for name, wf in wfs.items():
        assert wf.get("jobs"), f"{name} sin jobs"
        assert True in wf or "on" in wf, f"{name} sin disparadores"   # PyYAML lee `on:` como True


def test_every_action_is_pinned():
    for name, wf in workflows().items():
        for u in uses_of(wf):
            ref = u.split("@")[1] if "@" in u else ""
            assert re.fullmatch(r"v?\d+(\.\d+){0,2}|[0-9a-f]{40}", ref), f"{name}: {u} no está fijada a versión o SHA"


def test_every_workflow_declares_least_privilege_permissions():
    for name, wf in workflows().items():
        assert "permissions" in wf, f"{name} debe declarar permissions (mínimo privilegio)"


def test_no_pull_request_target_and_no_hardcoded_secrets():
    for p in WORKFLOWS.glob("*.yml"):
        assert "pull_request_target" not in p.read_text(encoding="utf-8"), f"{p.name} usa pull_request_target"
    for p in ROOT.rglob("*"):
        if p.is_file() and p.suffix in {".yml", ".yaml", ".py", ".env", ".json", ".md", ".properties"} and ".git/" not in str(p):
            assert not re.search(r"sk-ant-[A-Za-z0-9_-]{20,}", p.read_text(encoding="utf-8", errors="ignore")), f"posible clave en {p}"


def test_env_file_is_not_committed():
    assert not (ROOT / ".env").exists()
    assert (ROOT / ".env.example").exists()


def test_integrated_compose_wires_agent_and_both_stacks():
    c = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
    assert len(c["include"]) == 2 and "agent" in c["services"]
    assert "agent" in c["services"]["agent"]["profiles"]


# ------------------------------------------------------------------ DEBER (rojo hasta entregar)
def test_s1_coverage_gate_in_pom():
    pom = (LAB / "pom.xml").read_text(encoding="utf-8")
    assert "jacoco-maven-plugin" in pom, "falta JaCoCo en pom.xml"
    m = re.search(r"<minimum>\s*([0-9.]+)\s*</minimum>", pom)
    assert m and float(m.group(1)) >= 0.60, "el umbral de cobertura debe ser >= 0.60 (regla `check` ligada a `verify`)"
def test_s1_image_scan_in_pipeline():
    assert any(u.startswith("aquasecurity/trivy-action") for wf in workflows().values() for u in uses_of(wf)), "falta escaneo de imágenes (Trivy)"
def test_s1_cd_has_staging_deploy_with_approval_gate():
    cd = workflows().get("cd.yml")
    assert cd, "falta cd.yml"
    deploys = [j for j in cd["jobs"].values() if (j.get("environment") in ("staging",) or (isinstance(j.get("environment"), dict) and j["environment"].get("name") == "staging"))]
    assert deploys, "falta un job con `environment: staging` (el entorno exige aprobación manual en Settings)"
    assert any("images" in (j.get("needs") if isinstance(j.get("needs"), list) else [j.get("needs")]) for j in deploys), "el deploy debe depender de `images`"
def test_s2_trips_endpoint_and_tests_exist():
    res = list((LAB / "src/main/java").rglob("TripResource.java"))
    assert res and '@Path("/api/trips")' in res[0].read_text(encoding="utf-8"), "falta TripResource con @Path(\"/api/trips\")"
    assert list((LAB / "src/test/java").rglob("Trip*Test.java")), "faltan pruebas Trip*Test.java"
    assert any("outbox" in p.read_text(encoding="utf-8").lower() for p in (LAB / "src/main/java").rglob("*.java")), "falta el patrón Outbox"
def test_s4_observability_of_agent():
    assert "agent:8090" in (LAB / "infra/prometheus/prometheus.yml").read_text(encoding="utf-8"), "Prometheus no raspa al agente (agent:8090)"
    assert any("logistpulse_agent_" in p.read_text(encoding="utf-8") for p in (LAB / "infra/grafana/dashboards").glob("*.json")), "ningún panel usa métricas logistpulse_agent_*"
def test_s5_supply_chain_and_ownership():
    dep = ROOT / ".github" / "dependabot.yml"
    assert dep.exists(), "falta .github/dependabot.yml"
    eco = {u["package-ecosystem"] for u in yaml.safe_load(dep.read_text(encoding="utf-8"))["updates"]}
    assert {"maven", "pip", "docker", "github-actions"} <= eco
    assert (ROOT / ".github" / "CODEOWNERS").exists(), "falta CODEOWNERS"
    assert any(u.startswith("github/codeql-action") for wf in workflows().values() for u in uses_of(wf)), "falta análisis CodeQL"
