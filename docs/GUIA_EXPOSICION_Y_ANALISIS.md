# Guía común · Exposición y análisis estratégico del Proyecto final

## El objetivo no es el agente: es decidir mejor en logística
La pregunta gerencial es **cuánto mejora la operación logística** al decidir con datos, optimización y ejecución confiable. El agente de IA es solo el mecanismo que propone; lo que se evalúa son **KPIs de negocio**:

| KPI | Pregunta | Dónde se ve |
|---|---|---|
| **Despachos fallidos** | ¿Cuántos pedidos fallan por error de planificación, duplicado o batería mal estimada? | `base/decision_lab`, tablero BD |
| **SLA al cliente** | ¿Qué % llega a tiempo, y en el segmento corporativo? | `base/decision_lab`, OTIF del lakehouse |
| **Costo operativo** | ¿Costo por pedido: movimiento + retrabajo + penalidades? | `base/decision_lab` |
| **Personal** | ¿Cuántas horas-persona de planificación se liberan (FTE)? | `base/decision_lab` |

**El sistema ya está construido y probado**, y trae un **laboratorio de decisión** (`make decision-lab`) que compara la operación manual con el sistema bajo varios escenarios (normal, pico, flota reducida, manual sin errores). `make autonomia` compara además **nivel 1** (una persona aprueba cada viaje) con **nivel 2** (solo los riesgosos): cada equipo debe elegir y defender uno con esas cifras. Sus resultados están en `docs/RESULTADOS_LAB_DECISION.md`. **Son una simulación con supuestos ilustrativos**: el equipo debe poder decir qué parte del beneficio nace del modelo y cuál de un supuesto, y qué dato real mediría para confirmarlo. Cada materia mira el mismo sistema desde su ángulo y entrega **su propio** paquete, sin depender de las demás.

## Qué se entrega (por materia)
| Entregable | Formato | Peso interno |
|---|---|---|
| 1. **Demostración en vivo** del componente de su materia | 4 min, sin diapositivas, sobre el sistema corriendo | ver rúbrica |
| 2. **Exposición** | 12 min en total (incluye la demo) + 5 min de preguntas del jurado | |
| 3. **Análisis estratégico** | `informe/PLANTILLA_ANALISIS.md` completada, **máx. 4 páginas** | |
| 4. **Declaración de uso de IA** | 1 párrafo: qué herramienta, para qué, qué verificaron a mano | obligatoria |

**Defensa individual (factor 0–1):** 5 min por persona. Cada integrante responde preguntas sobre cualquier parte de *su* materia. La nota del equipo se multiplica por el factor individual.

## Estructura del análisis estratégico (las 5 secciones)
1. **La decisión.** Qué decisión de **logística** (política de despacho, inversión en flota u optimización, nivel de servicio, personal) debe tomar la gerencia y con qué **KPI y evidencia** (laboratorio de decisión, medición propia) la respaldan.
2. **Alternativas.** Mínimo tres, incluida «no hacer nada» y una «comprar/usar servicio externo». Qué se pierde con cada una.
3. **Costos, beneficios y supuestos.** Ahorro **neto** (resten implantación, mantenimiento y capacitación), con cifras con fuente o **marcadas como supuesto**. Qué dato real cambiaría su conclusión.
4. **Riesgos, gobernanza y límites.** Qué puede salir mal, quién responde, qué controles existen y **qué no se pudo verificar** (sea explícito: ver «Limitaciones» del README raíz).
5. **Recomendación y conexión con el Deber 3.** Qué nivel de autonomía del agente (1–4) recomiendan, por qué, y qué cambiarían respecto de lo que concluyeron en la revisión de literatura.

## Rúbrica (30 puntos) — la misma estructura en todas las materias
El proyecto final vale **30 puntos por materia**; la nota es del equipo multiplicada por un factor individual (0 a 1) que fija una sustentación oral de 5 minutos.
| Criterio | Pts | Excelente (≥ 90 %) | Insuficiente (< 50 %) |
|---|---|---|---|
| Dominio técnico demostrado | 7,5 | Corren el sistema, **modifican un parámetro en vivo** y predicen el resultado; explican el código sin leer | Solo muestran capturas; no predicen resultados |
| Calidad del análisis estratégico | 9,0 | Decisión clara, ≥ 3 alternativas comparadas con criterios explícitos, supuestos señalados | Descripción técnica sin decisión ni alternativas |
| Riesgos, gobernanza y límites | 4,5 | Riesgos concretos con dueño y control; reconocen lo no verificado | Riesgos genéricos («puede fallar») |
| Conexión con Deber 3 (agentes, autonomía) | 3,0 | Vinculan hallazgos del sistema con su recomendación previa | Sin conexión |
| Exposición (claridad y tiempo) | 3,0 | 12 min exactos, un mensaje por diapositiva, sin leer | Se pasan > 2 min o leen |
| Respuesta a preguntas | 3,0 | Responden con evidencia o dicen «no lo sé, lo verificaría así…» | Inventan o evaden |

## Microservicios y APIs dirigidas por contrato (eje transversal)
El proyecto no solo decide mejor: lo hace con **servicios que se acuerdan por contrato**. Lectura: [`ARQUITECTURA_MICROSERVICIOS_API_FIRST.md`](ARQUITECTURA_MICROSERVICIOS_API_FIRST.md) y [`API_PRODUCT_CANVAS.md`](API_PRODUCT_CANVAS.md); contratos en `contracts/`. Lo evalúan sobre todo Desarrollo de SW (contrato, versionado, CI) y Diseño de Sistemas (descomposición, ADR-001, eventos); Bases de Datos (consumidor de eventos, calidad) y Teoría (el solver es un puerto con contrato estable) lo mencionan donde les toca. Esta sección no añade entregables: afina el criterio de «Dominio técnico» y «Riesgos».

## Datos reales y datos de referencia
Los números del laboratorio de decisión son supuestos. Dos vías para respaldarlos: (1) **datos públicos de referencia** (`make contraste`, Olist y Favorita; no son de DANEC) y (2) **datos de DANEC** pedidos con `docs/SOLICITUD_DATOS_DANEC.md` en la visita técnica. Todo análisis debe declarar qué supuesto sigue sin respaldo.

## Seguridad del pipeline y de la API (eje transversal)
La API tiene clave por cliente con permisos, límite de tasa, `X-Request-Id` y un gateway Kong delante; el repositorio trae pipelines de SAST/SCA y de DAST que corren en GitHub Actions. Todo está **escrito pero sin ejecutar en GitHub ni compilado con Maven** (ver `docs/SEGURIDAD_CICD.md` §7): la primera corrida real es parte del trabajo del estudiante y se evalúa lo que encuentra y cómo lo decide.

## Cómo se pone a funcionar (cualquier materia)
```bash
make test                         # 309 pruebas deben pasar, sin Docker
make decision-lab                 # KPIs: fallidos, SLA, costo, horas-persona (simulación)
make autonomia                    # nivel 1 vs nivel 2 de autonomía
make cadena                       # cadena completa: inventario → pedidos → reposición → packing → despacho, una etapa a la vez
make agent-local                  # agente en :8090 con datos de ejemplo
curl -s -X POST localhost:8090/plan
curl -s -X POST -H 'X-Approver: su.nombre' localhost:8090/proposals/<id>/approve
make up && make lakehouse-data    # (opcional) stack completo con Docker
```

## Banco de preguntas transversal (el jurado sortea 3)
1. ¿Qué parte del ahorro simulado nace del **modelo** y cuál de un **supuesto**? ¿Qué dato real mediría para confirmarlo?
2. ¿Qué parte del sistema es **determinista** y cuál **probabilística**? ¿Por qué importa la frontera?
2. Si el modelo de lenguaje se cae o alucina códigos, ¿qué pasa? Muéstrenlo.
3. ¿Qué evidencia tienen de que el sistema **funciona** y cuál es la evidencia de que **no** lo comprobaron?
4. ¿Quién es responsable si una propuesta aprobada por una persona causa un daño? ¿Qué registro lo demuestra?
5. Suban la flota 10 ×: ¿qué se rompe primero y cuánto cuesta arreglarlo?
6. ¿Qué pasaría si subimos al agente de nivel 1 a nivel 2 (ejecuta sin aprobar para casos de bajo riesgo)? ¿Qué controles faltan?
7. ¿Qué métrica mostraría ante un directivo para demostrar valor? ¿Cuál escondería y por qué sería un error esconderla?
8. ¿Qué dependería de un proveedor externo y qué costo de salida tendría?
9. **(Microservicios/APIs)** ¿Qué cambio al contrato de un evento o endpoint es compatible y cuál exige `/v2`? ¿Cómo se detecta antes de producción? (`contracts/`)
10. **(Microservicios/APIs)** ¿Por qué Pedidos y Flota siguen juntos (ADR-001)? ¿Qué disparador medible justificaría separarlos y qué métrica de negocio se vería afectada?
11. **(Microservicios/APIs)** Un evento llega dos veces: ¿qué KPI se distorsiona (SLA, despachos) y dónde se deduplica?
12. **(API/seguridad)** Jersey y Kong, ¿quién hace qué? ¿Por qué la clave y el límite de tasa se aplican en los dos? (`docs/ARQUITECTURA_MICROSERVICIOS_API_FIRST.md` §8)
13. **(API/seguridad)** Un cliente reintenta tras un 429 sin esperar `Retry-After`: ¿cómo se ve en despachos fallidos y en horas-persona? Si Redis cae, ¿abrir o cerrar el límite?
14. **(DevSecOps)** ¿Qué detecta SAST que DAST no, y al revés? ¿Por qué el DAST corre en dos fases? Muestre un hallazgo real y diga si lo arregló, lo aceptó con razón o lo excluyó (`docs/SEGURIDAD_CICD.md`).

## Declaración de uso de IA (plantilla)
> Usamos [herramienta] para [tarea]. Verificamos [qué] a mano mediante [cómo]. No verificamos [qué]. Cada integrante puede explicar y defender lo entregado.

## Contexto para la discusión (WEF / Deber 3)
Conecten sus conclusiones con lo investigado en el Deber 3 (contexto del Foro Económico Mundial sobre adopción de agentes y cambio de tareas laborales, modelos/plataformas y costos). Citen **las fuentes que ya revisaron**; no agreguen cifras que no puedan respaldar.
