# LOGISTPULSE · Proyecto final (zip base)

Un **sistema de decisión logística** cuyo objetivo es **reducir despachos fallidos, mejorar el SLA y bajar costo y horas-persona** (con un **agente de IA que sugiere**; una persona aprueba), integrado con el **lakehouse** (Bases de Datos), el **lab de la API** (Desarrollo de SW) y el **simulador P/NP** (Teoría de la Computación). El agente arma viajes multi-parada para los robots AMR; el orden de paradas es un problema **tipo NP** (TSP en versión de decisión) resuelto por algoritmos y **verificado** con un certificado antes de proponerse.

> Lectura previa: [`docs/ANALISIS_INTEGRACION.md`](docs/ANALISIS_INTEGRACION.md) (decisiones, hallazgos y qué se verificó).

```
logistpulse-proyecto-final/
├─ base/                       ← sistema ya construido (lo entrega el docente)
│  ├─ lakehouse/               Postgres (ODS·DW·marts) + MinIO + Redpanda + Grafana  (+ sql/04_agent.sql: esquema del agente)
│  ├─ lab/                     API Jersey/Spring + A* + viajes multi-parada (idempotencia + Outbox) + Redis + RabbitMQ + Prometheus + Grafana
│  ├─ decision_lab/            Laboratorio de decisión: manual vs sistema → fallidos, SLA, costo, horas-persona (simulación)
│  └─ agent/                   lpagent: agente de despacho (puertos, validador, respaldo, API de aprobación, auditoría)
├─ deberes/                    ← UNA carpeta por materia: exposición + análisis estratégico, independientes entre sí
│  ├─ teoria-computacion/      np_lab: Held-Karp, 2-opt, DPLL, 2-aproximación, benchmark + simulador HTML
│  ├─ bases-de-datos/          SQL (1FN, mart de KPIs, ingesta, privilegios) + 11 controles de calidad (incluye inventario, reposición y packing) + panel Grafana
│  ├─ desarrollo-software/     contrato /api/trips, actuador, pipeline CI/CD (JaCoCo, Trivy, CodeQL, staging, Dependabot)
│  └─ diseno-sistemas/         lp_patterns: Command, Strategy, Observer, Template Method, Decorator, Adapter
├─ .github/workflows/          CI por área y CD por etiqueta vX.Y.Z
├─ contracts/                  API-first: OpenAPI (fleet-orders, dispatch-decision) · AsyncAPI (eventos) · JSON Schema · catálogo · línea base · validador
├─ docs/                       ANALISIS_INTEGRACION.md · GUIA_EXPOSICION_Y_ANALISIS.md · ARQUITECTURA_MICROSERVICIOS_API_FIRST.md (ADR-001) · API_PRODUCT_CANVAS.md
├─ docker-compose.yml          stack integrado (include de lab + lakehouse, perfil "agent")
└─ Makefile · .env.example · .devcontainer/
```

## Qué hace el equipo de estudiantes
**No programa el sistema: lo pone a funcionar, lo expone y decide con criterio estratégico.** Cada materia entrega demostración en vivo (4 min) + exposición (12 min) + análisis estratégico (≤ 4 págs) + declaración de uso de IA, con defensa individual. Detalles y rúbrica en [`docs/GUIA_EXPOSICION_Y_ANALISIS.md`](docs/GUIA_EXPOSICION_Y_ANALISIS.md).

## Quién mira qué
| Materia | Carpeta | Aporta al agente | Pregunta estratégica central |
|---|---|---|---|
| Teoría | `deberes/teoria-computacion/` | solver NP (`LP_SOLVER_PLUGIN=np_lab.plugin:build`) | ¿Qué garantía puede prometer el negocio: óptimo, heurística o servicio externo? |
| Bases de Datos | `deberes/bases-de-datos/` | prioridades y auditoría (`LP_DATA_PLUGIN`, `LP_AUDIT_PLUGIN`) | ¿Qué calidad de dato se exige antes de que el agente proponga? |
| Desarrollo de SW | `deberes/desarrollo-software/` (+ `base/lab`, `.github`) | actuador (`LP_ACTUATOR_PLUGIN=lp_dsm.actuator:build`) | ¿Qué mínimo de entrega segura antes de dejar actuar a un agente? ¿Cómo se gobiernan contratos y versiones sin romper a los consumidores? |
| Diseño de Sistemas | `deberes/diseno-sistemas/` | composición con patrones (`lp_patterns.compose`) | ¿Qué patrones valen su complejidad y cuáles son sobre-ingeniería? ¿Monolito modular o microservicios (ADR-001)? |

Cada deber usa solo `base/` y su carpeta: puede entregarse aunque los demás no lo hagan.

## Arranque rápido
```bash
make test                      # 309 pruebas (solo Python; sin Docker; incluye contratos, gateway y humo de seguridad)
make contratos                 # valida contratos y compatibilidad contra contracts/baseline
make lab-teoria                # JupyterLab con el notebook de Teoría sobre el lakehouse
make contraste OLIST=... FAVORITA=...   # contrasta supuestos con datos públicos (Kaggle, tras descargarlos)
make decision-lab              # KPIs de negocio: despachos fallidos, SLA, costo y horas-persona (simulación)
make cadena                    # cadena completa: inventario → pedidos → reposición → packing → despacho, una etapa a la vez
make autonomia                 # ¿aprobar cada viaje (nivel 1) o solo los riesgosos (nivel 2)? KPIs de cada uno
make agent-local               # agente en :8090 con datos de ejemplo, sin Docker (escucha solo en 127.0.0.1)
make sast                      # SAST/SCA local de Python (Bandit + pip-audit); en GitHub corre ci-seguridad-sast.yml
curl -s -X POST localhost:8090/plan                                  # propone un viaje (no ejecuta nada)
curl -s -X POST -H 'X-Approver: tu.nombre' localhost:8090/proposals/<id>/approve   # una persona aprueba

make up                        # lab + lakehouse con Docker (≈ 8 GB RAM; en Codespaces usa 4 núcleos)
make lakehouse-data            # seed + ETL + ML
make up-agent LP_MODE=lab      # agente leyendo el lab vivo (añade LP_EXECUTE=1 para que ejecute lo aprobado)
make up-gateway                # + gateway Kong :8000 (clave X-Api-Key, permisos, rate limit, /api/v1)
make seguridad-smoke           # comprueba 401/403/429 y X-Request-Id contra el stack vivo; `make dast` lanza OWASP ZAP
```
| Servicio | URL |
|---|---|
| API + consola del lab | http://localhost:8080 (en modo docker exige `X-Api-Key`; claves de desarrollo en `docs/SEGURIDAD_CICD.md` y `base/lab/README.md`) |
| Gateway / API manager (perfil `gateway`) | http://localhost:8000 → `/api/v1/**`, `/decision/v1/**` |
| Agente (`/plan`, `/proposals`, `/metrics`) | http://localhost:8090 |
| Grafana lab / lakehouse | http://localhost:3001 / http://localhost:3000 (admin/admin) |
| Prometheus · RabbitMQ · MinIO · Jupyter | :9090 · :15672 (guest/guest) · :9001 · :8888 |

## Garantías de diseño del agente (autonomía nivel 1 de 4)
- **Planificar no actúa:** `/plan` nunca llama al actuador; solo crea una propuesta `PENDING_APPROVAL`.
- **Aprobar exige identidad** (`X-Approver`) y es de un solo uso.
- **El modelo elige pedidos, no recorridos:** el orden lo calcula el solver y lo verifica un validador determinista (certificado + batería + robot libre). Si el modelo inventa códigos o pide algo inviable, se usa el planificador de respaldo.
- **Sin modelo no hay problema:** por defecto el planificador es por reglas; `LP_PLANNER=llm` usa un modelo (requiere `ANTHROPIC_API_KEY` y `LP_LLM_MODEL`; adaptador **no probado** contra la API real).
- Todo queda en un registro de auditoría (JSONL; Postgres con el deber de BD).

## Limitaciones conocidas de esta entrega (léanlas antes de exponer)
- **Java sin compilar:** el docente no pudo ejecutar Maven (sin acceso a Maven Central) ni Docker. El código de viajes, Outbox, JaCoCo, los filtros de seguridad (clave, rate limit, request id) y las pruebas Java **no están verificados con Maven**; la lógica de los filtros sí se ejecutó contra *stubs* de JAX-RS; `mvn verify` en `base/lab` es la primera verificación real (parte del deber de Desarrollo de SW).
- **SQL sin ejecutar** contra Postgres: solo validado sintácticamente (pglast). `ci-bd` y `make db-apply db-check` lo ejecutan de verdad.
- **Workflows** validados como YAML, no ejecutados en GitHub. Trivy/CodeQL/staging requieren configuración del repositorio (environment `staging`, variable `STAGING_URL`, usuarios en `CODEOWNERS`).
- **Adaptador de LLM** (`llm_anthropic.py`) no probado contra la API real.
- Verificado aquí: pruebas Python (211), `docker compose config`, sintaxis SQL, YAML y el flujo HTTP del agente.
