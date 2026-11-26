# LOGISTPULSE · proyecto final — orquestación desde la raíz
DC = docker compose
PSQL_DOCKER = $(DC) exec -T postgres psql -U lp -d logistpulse
PYPATH = base/decision_lab:base/agent:deberes/teoria-computacion:deberes/bases-de-datos:deberes/desarrollo-software:deberes/diseno-sistemas

.PHONY: help up up-lab up-lakehouse up-agent up-gateway up-gateway-only lakehouse-data down reset smoke agent-local \
        db-apply db-check decision-lab test-decision test test-agent test-teoria test-bd test-dsm test-diseno test-contratos contratos autonomia sast sast-java sast-docker seguridad-smoke dast contraste lab-teoria db-teoria psql

help:            ## Lista de objetivos
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | sed 's/:.*##/ —/'

up:              ## Lab + lakehouse (sin agente)
	$(DC) up -d --build

up-lab:          ## Solo el lab (API, Postgres, Redis, RabbitMQ, WireMock, Prometheus, Grafana-ops)
	$(DC) up -d --build db redis rabbitmq carrier-mock api prometheus grafana-ops

up-lakehouse:    ## Solo el lakehouse (Postgres, MinIO, Grafana)
	$(DC) up -d --build postgres minio minio-init grafana

lakehouse-data:  ## seed + etl + ml del lakehouse
	$(DC) run --rm --build seed
	$(DC) run --rm etl
	$(DC) run --rm ml

up-agent:        ## Agente de despacho (usa los adaptadores de las variables LP_*_PLUGIN)
	$(DC) --profile agent up -d --build agent

up-gateway:      ## Gateway Kong en :8000 (claves, permisos, rate limit, /api/v1). Las APIs siguen también en :8080/:8090
	$(DC) --profile gateway --profile agent up -d --build gateway agent

up-gateway-only: ## Igual, pero 8080/8090 dejan de publicarse: la única entrada es :8000
	$(DC) -f docker-compose.yml -f docker-compose.gateway-only.yml --profile gateway --profile agent up -d --build gateway agent

agent-local:     ## Agente sin Docker en :8090 (LP_MODE=fixture por defecto). Ej.: make agent-local LP_SOLVER_PLUGIN=np_lab.plugin:build
	PYTHONPATH=$(PYPATH) python3 -m lpagent.server

smoke:           ## Prueba de humo del lab (necesita el lab arriba)
	bash base/lab/scripts/smoke.sh

db-apply:        ## Aplica los scripts SQL del deber de Bases de Datos
	PSQL="$(PSQL_DOCKER)" deberes/bases-de-datos/scripts/db_apply.sh

db-check:        ## Corre los controles de calidad (Data Trust Gate)
	PSQL="$(PSQL_DOCKER)" deberes/bases-de-datos/scripts/db_check.sh

psql:
	$(PSQL_DOCKER)

test: test-agent test-decision test-teoria test-bd test-dsm test-diseno test-contratos   ## Pruebas de la BASE de todo (todas deben pasar)

test-contratos:  ## Pruebas de contrato (OpenAPI/AsyncAPI/JSON Schema + agente real)
	PYTHONPATH=$(PYPATH) python3 -m pytest contracts/tests -q

lab-teoria:      ## JupyterLab (:8888) con el notebook de Teoría (carpeta «teoria»). Necesita el lakehouse arriba
	$(DC) -f docker-compose.yml -f docker-compose.jupyter-teoria.yml --profile lab up -d jupyter

db-teoria:       ## Crea teoria.solver_run en un lakehouse YA creado (en uno nuevo lo hace initdb)
	$(DC) exec -T postgres psql -U lp -d logistpulse < base/lakehouse/sql/05_teoria.sql
	$(DC) exec -T postgres psql -U lp -d logistpulse -c "GRANT USAGE ON SCHEMA teoria TO lp_reader; GRANT SELECT ON ALL TABLES IN SCHEMA teoria TO lp_reader;"

contraste:       ## Contrasta supuestos con Olist/Favorita. Ej.: make contraste OLIST=datos/olist FAVORITA=datos/favorita
	PYTHONPATH=$(PYPATH) python3 -m refdata.calibrar $(if $(OLIST),--olist $(OLIST)) $(if $(FAVORITA),--favorita $(FAVORITA)) --out docs/CONTRASTE_SUPUESTOS.md

sast:            ## SAST/SCA local de Python: Bandit + pip-audit (los mismos que corre GitHub Actions). pip install bandit pip-audit
	bandit -r base/agent base/decision_lab deberes contracts/tools base/lakehouse -c .bandit -x '*/tests/*,deberes/bases-de-datos/ci/*' -ll
	pip-audit -r base/lakehouse/services/requirements.txt

sast-java:       ## SAST de Java: SpotBugs + Find Security Bugs (perfil sast del pom)
	cd base/lab && mvn -B -Psast -DskipTests compile spotbugs:check

sast-docker:     ## Semgrep y Trivy con Docker (no instalas nada): reglas OWASP, secretos y CVE de dependencias
	docker run --rm -v "$(CURDIR):/src" -w /src semgrep/semgrep semgrep scan --metrics=off --error --config p/owasp-top-ten --config p/java --config p/python --config p/dockerfile .
	docker run --rm -v "$(CURDIR):/src" -w /src aquasec/trivy:0.58.0 fs --scanners vuln,secret --severity CRITICAL,HIGH --ignore-unfixed --exit-code 1 --config base/gateway/trivy.yaml .

seguridad-smoke: ## DAST fase 1: 401/403/429 y X-Request-Id contra el stack vivo (make up-gateway antes)
	python3 contracts/tools/security_smoke.py --gateway http://localhost:8000 --service http://localhost:8080

dast:            ## DAST fase 2: OWASP ZAP contra los contratos (necesita Docker y el stack arriba). Informes en zap-out/
	bash base/gateway/run_zap.sh fleet-orders.v1.yaml http://localhost:8080 zap-fleet-orders lab-dev-dispatcher-key zap-out; test $$? -le 2
	bash base/gateway/run_zap.sh dispatch-decision.v1.yaml http://localhost:8090 zap-dispatch-decision lab-dev-dispatcher-key zap-out; test $$? -le 2

contratos:       ## Valida contratos y compatibilidad contra contracts/baseline
	python3 contracts/tools/validate_contracts.py

cadena:          ## Cadena completa: inventario → pedidos → reposición → packing → despacho, una etapa a la vez (KPIs por etapa)
	cd base/decision_lab && PYTHONPATH=../agent:. python -m decision_lab.run --cadena

autonomia:       ## Nivel de autonomía: ¿que una persona apruebe cada viaje (nivel 1) o solo los riesgosos (nivel 2)? KPI de ambos
	PYTHONPATH=base/agent:base/decision_lab python3 -m decision_lab.run --autonomia

test-agent:
	cd base/agent && python3 -m pytest -q

test-decision:
	cd base/decision_lab && python3 -m pytest -q

decision-lab:    ## KPIs de negocio: fallidos, SLA, costo y horas-persona (simulación)
	PYTHONPATH=base/agent:base/decision_lab python3 -m decision_lab.run

test-teoria:
	cd deberes/teoria-computacion && python3 -m pytest -q

test-bd:
	cd deberes/bases-de-datos && python3 -m pytest -q

test-dsm:
	cd deberes/desarrollo-software && python3 -m pytest -q

test-diseno:
	cd deberes/diseno-sistemas && python3 -m pytest -q

down:
	$(DC) --profile agent --profile streaming --profile lab --profile jobs down

reset:           ## Borra TODOS los volúmenes (reinicia Postgres desde cero)
	$(DC) --profile agent --profile streaming --profile lab --profile jobs down -v
