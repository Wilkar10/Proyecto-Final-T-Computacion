# Proyecto final · Desarrollo de Software Moderno — «Entregar rápido sin romper el despacho»

> **Empiecen por `HOJA_DE_ACCIONES.md`** (1 página): pasos exactos, qué deben ver y las decisiones a defender.

**Qué es:** la pieza de Desarrollo de SW del proyecto final LOGISTPULSE, **ya implementada** pero con una salvedad crítica: **el código Java y el CI/CD no pudieron compilarse ni ejecutarse donde se preparó el material** (sin acceso a Maven Central ni Docker). Parte de su trabajo es **ser la primera verificación real**: correr `mvn verify`, reportar lo que falle y decidir qué tan confiable es la entrega. Es independiente de los otros deberes.

**Dónde se conecta:** al aprobar una propuesta, el actuador hace **un único** `POST /api/trips` con `Idempotency-Key = proposal_id`; el lab asigna **todos** los pedidos al mismo robot, descuenta la batería del ciclo completo y publica eventos por **Outbox**.

## Su aporte a los KPI de negocio
**KPI que mueve:** **despachos fallidos** (duplicados, pedidos perdidos, eventos no publicados) y **tiempo de decisión a ejecución**. Idempotencia, todo-o-nada y Outbox son lo que sostiene el supuesto «0,5 % de error residual» del sistema.
**Evidencia del lab de decisión:** de los despachos fallidos manuales, una parte es «error» (captura, duplicado, olvido) que la ejecución confiable elimina. Su análisis debe responder: ¿qué tasa real de error residual pueden defender, cómo la medirían en producción (SLO, métricas) y qué costo tiene reducirla de 0,5 % a 0,1 %?

## Qué contiene (todo implementado; Java sin verificar)
| Ruta | Qué hay |
|---|---|
| `api/trips.openapi.yaml` | Contrato (contract-first): 201/200/400/404/409/422, todo-o-nada |
| `../../base/lab/src/main/java/.../service/TripTx.java` · `TripService.java` · `api/TripResource.java` | Viaje atómico, idempotencia (UNIQUE sobre la clave, carrera resuelta devolviendo el ganador) |
| `.../domain/Trip.java` · `OutboxEvent.java` · `messaging/OutboxPublisher.java` | **Outbox** transaccional + relé `@Scheduled` (al menos una vez) |
| `.../service/OrderService.java` | Modificado: pedidos de un viaje no descuentan batería dos veces; el robot se libera con el último |
| `../../base/lab/src/test/java/.../TripServiceTest.java` | 7 pruebas (incluye concurrencia con la misma clave) |
| `../../base/lab/pom.xml` | **JaCoCo**: el build falla si la cobertura de líneas < 0,60 |
| `../../.github/workflows/` | `ci-lab` (+ **Trivy**), `ci-deber-dsm`, **CodeQL**, `cd` con `deploy-staging` (aprobación manual, health check, reversa), `dependabot.yml`, `CODEOWNERS` |
| `lp_dsm/actuator.py` | `TripActuator`: POST único, reintentos solo 5xx/red (máx. 2), errores propagados |
| `../../base/lab/infra/` | Scrape de Prometheus del agente y paneles de Grafana (`logistpulse_trips_total`, repeticiones, propuestas) |

## Microservicios y APIs dirigidas por contrato (API-first)
Esta materia es la dueña del **contrato y su cumplimiento**. Lean `../../docs/ARQUITECTURA_MICROSERVICIOS_API_FIRST.md` (contextos acotados, ADR-001), `../../docs/API_PRODUCT_CANVAS.md` y la carpeta `../../contracts/` (OpenAPI, AsyncAPI, JSON Schema, catálogo, línea base).
```bash
make contratos           # valida catálogo, $ref, ejemplos y compatibilidad contra contracts/baseline
make test-contratos      # 10 pruebas; incluye el AGENTE REAL contra su OpenAPI
```
**Deriva conocida que deben cerrar o dictaminar** (el contrato manda): hoy el lab publica solo el id del pedido en la cola `orders.dispatched`, sin *envelope* ni `trip.created`. Deben (a) reproducir la deriva, (b) decidir si se corrige el código o el contrato —y quién consume el evento hoy—, y (c) si corrigen, emitir el envelope al exchange `logistpulse.events`, y mostrar que `validate_contracts.py` y el pipeline lo detectan. Rompan **a propósito** el contrato (quiten un campo del esquema, agreguen un parámetro requerido) y muestren cómo el CI lo bloquea.

## Seguridad en el pipeline: SAST, DAST y la capa de API (DevSecOps)

Los pipelines viven en el repositorio y corren en GitHub Actions: `ci-seguridad-sast.yml` (análisis estático: Bandit, SpotBugs + Find Security Bugs, Semgrep, pip-audit, Trivy) y `ci-seguridad-dast.yml` (levanta el stack y lo ataca: humo de 401/403/429 + OWASP ZAP usando los OpenAPI como mapa). Guía completa, ajustes de GitHub y límites en `docs/SEGURIDAD_CICD.md`. El lab ahora tiene `X-Api-Key` con permisos, rate limit (token bucket) y `X-Request-Id`; delante hay un gateway Kong (`base/gateway/kong.yml`).

Decisiones de seguridad que deben tomar (con los informes ya generados por el pipeline; no hace falta programar):
1. **¿Se despliega?** Ante el informe de hallazgos (SpotBugs, Semgrep, Trivy, ZAP): por cada uno, *arreglar*, *aceptar con razón escrita* o *excluir*, como la tabla de §5 de ese documento.
2. **¿Por qué el límite de tasa está igual en tres lugares** (lab, gateway, contrato)? Observen en el CI qué falla si solo se cambia uno (`contracts/tests/test_gateway.py`) y decidan quién es dueño del número.
3. **Si Redis cae, ¿fail-open o fail-closed?** Hoy el lab sigue con límite en memoria. Argumenten con despachos fallidos y riesgo de abuso cuál prefieren.
4. **¿Qué puertas del pipeline son obligatorias y cuáles solo informativas?** (hoy Trivy de configuración es informativo).

## Ponerlo a funcionar
```bash
make test-dsm                                   # 19 pruebas Python (estructura de workflows, actuador) — verdes
cd base/lab && mvn -B verify                    # el docente lo corre primero; ustedes revisan resultado y cobertura
make up-lab && make smoke                       # con Docker
LAB_URL=http://localhost:8080 python -m pytest deberes/desarrollo-software/tests/test_contract.py   # contrato contra el lab vivo
```
> **Entregable especial:** una nota de «auditoría de la entrega» (≤ 1 página): qué mostraron los informes del pipeline, qué decidieron (arreglar / aceptar / excluir) y por qué. **El docente corre antes la primera `mvn verify` real** y deja el resultado disponible.

## Qué deben exponer (12 min) — guion sugerido
1. **Contrato y atomicidad** (2 min): por qué contract-first (OpenAPI + AsyncAPI); catálogo ≠ contrato; «todo o nada» (409 sin efectos parciales).
2. **Idempotencia y Outbox** (3 min): qué evita el doble despacho, qué garantía da el Outbox (**al menos una vez**, no exactamente una) y qué debe hacer el consumidor.
3. **Demo en vivo** (4 min): `POST /api/trips` con la misma clave **dos veces** (201 y luego 200, batería descontada una sola vez); un viaje sin batería (409, nada cambia).
4. **Pipeline y cadena de suministro** (2 min): puertas de calidad, Trivy/CodeQL/Dependabot, despliegue con aprobación y reversa.
5. **Análisis estratégico** (1 min): decisión y recomendación.

## Preguntas que debe poder responder el equipo
- ¿Qué cambio al contrato es **compatible** (MINOR) y cuál exige `/v2`? Den un ejemplo de cada uno sobre `trip.created`.
- Si el consumidor recibe `order.dispatched` dos veces, ¿qué campo usa para deduplicar y dónde guardaría lo ya visto?
- ¿Qué parte del contrato **no** puede validar un linter (comportamiento, atomicidad)? ¿Cómo la cubren?
- ¿Qué pasa si el proceso cae entre el commit y la publicación? ¿Y entre publicar y marcar como publicado?
- ¿Por qué `TripService` **no** es `@Transactional` y `TripTx` sí?
- ¿Es 60 % de cobertura un buen umbral? ¿Qué NO mide la cobertura?
- Trivy falla el build con vulnerabilidades HIGH sin corrección disponible: ¿bloquear o no? Costo de cada opción.
- ¿Qué métricas DORA tendría este equipo y cuáles de ellas dependen del pipeline entregado?
- ¿Qué haría falta para que el agente pudiera **desplegar** su propio código? (Pista: autonomía nivel 3–4.)

## Análisis estratégico — escenarios (elijan UNO)
- **A. Incidente.** Un viaje se despachó dos veces en producción. Reconstruyan causas posibles, qué control debió impedirlo, y la política de reversa.
- **B. Velocidad vs seguridad.** La dirección pide desplegar a diario. ¿Qué puertas conservan, cuáles automatizan, cuáles cuestan demasiado?
- **C. Build vs buy.** ¿Mantener su pipeline o contratar una plataforma de entrega? Criterios, costos y dependencia del proveedor.
- **D. Gobierno de APIs.** Tres equipos consumirán `fleet-orders`. ¿Qué versionado, catálogo (¿Backstage?) y validación en CI exigirían, y qué costo tiene para la velocidad? Qué pasa con `/api` sin `/v1`.
- **E. Cadena.** Con `make cadena`, ¿qué etapa convierten primero en servicio con contrato propio y por qué? Hoy solo pedidos y despacho tienen contrato; inventario, reposición y packing viven en el simulador.

## Entregables y evaluación
Formato, rúbrica (30 puntos), defensa individual y declaración de uso de IA: **`../../docs/GUIA_EXPOSICION_Y_ANALISIS.md`** (común a todas las materias). Plantilla del análisis: `informe/PLANTILLA_ANALISIS.md`.

| Criterio | Pts | Qué miraremos específicamente en esta materia |
|---|---|---|
| Dominio técnico demostrado | 7,5 | Revisan el resultado de `mvn verify` y del CI, demuestran el viaje atómico con la misma `Idempotency-Key` dos veces y **muestran el CI bloqueando un cambio incompatible del contrato** |
| Calidad del análisis estratégico | 9,0 | Mínimo aceptable de entrega antes de dejar a un agente actuar: costo vs riesgo, indicadores DORA, build vs buy |
| Riesgos, gobernanza y límites | 4,5 | Seguridad de la cadena de suministro, reversa, qué NO se verificó (el Java no fue compilado por el docente) |
| Conexión con Deber 3 | 3,0 | Nivel de autonomía recomendado y por qué; qué cambió respecto a la revisión de literatura |
| Exposición | 3,0 | 12 min exactos, un mensaje por diapositiva |
| Preguntas | 3,0 | Evidencia o «no lo sé, lo verificaría así» |

## Independencia
Este deber usa solo `base/` y su propia carpeta. Puede entregarse aunque los otros equipos no entreguen nada. Si quieren mostrar la integración, pueden activar su adaptador con la variable `LP_ACTUATOR_PLUGIN=lp_dsm.actuator:build` (opcional, no puntúa).
