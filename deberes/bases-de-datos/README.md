# Proyecto final · Bases de Datos — «El dato confiable antes que el agente»

> **Empiecen por `HOJA_DE_ACCIONES.md`** (1 página): pasos exactos, qué deben ver y las decisiones a defender.

**Qué es:** la pieza de Bases de Datos del proyecto final LOGISTPULSE, **ya implementada** (SQL, controles de calidad, ingesta, mart de KPIs y panel). Su trabajo es **entenderla, ejecutarla, exponerla y decidir** qué calidad de dato hace falta para que un agente pueda sugerir despachos. Es independiente de los otros deberes.

**Dónde se conecta:** el agente lee **prioridades** de cliente del lakehouse (segmento + OTIF) y escribe **propuestas y auditoría** en el esquema `agent`, con el rol de mínimo privilegio `lp_agent`.

## Su aporte a los KPI de negocio
**KPI que mueve:** *medirlos*. Sin línea base no hay ahorro demostrable. Su materia define **qué se mide, con qué calidad y quién es dueño**: % de despachos fallidos, OTIF/SLA por segmento, costo por pedido, aceptación de propuestas.
**Evidencia del lab de decisión:** el ahorro simulado depende de tasas **supuestas** (error humano 3 %, error del sistema 0,5 %, subestimación de costos 25 %). Su análisis debe decir **cómo se medirían de verdad** (qué tablas, qué consulta, qué control de calidad) y qué pasa con el ahorro si resultan distintas.

## Qué contiene (todo implementado)
| Ruta | Qué hay |
|---|---|
| `../../base/lakehouse/sql/04_agent.sql` | Base: esquema `agent` (propuestas con CHECK de invariantes, auditoría append-only, rol `lp_agent`) |
| `sql/10_proposal_stop.sql` | **Normalización 1FN**: `order_codes[]` → tabla `agent.proposal_stop (proposal_id, stop_seq)` con PK y FK |
| `sql/11_mart_agent.sql` | **Mart de KPIs** `mart_agent.kpis` (propuestas, tasa de aceptación, % de fallback, uso del presupuesto) |
| `sql/12_lab_ingest.sql` | Destino de la **ingesta idempotente** `ods.lab_order` (PK = code) |
| `sql/13_privilege_tests.sql` | **Pruebas de mínimo privilegio**: `lp_agent` intenta `DELETE/UPDATE` y debe recibir `insufficient_privilege` |
| `sql/14_inventory_chain.sql` · `15_inventory_seed.sql` | **Inventario → reposición → packing**: `inv.sku`, `stock_level`, `stock_movement` (libro de solo inserción), `purchase_order`, `packing_job/box` y vistas `mart_ops.v_stock_coverage` / `v_packing_efficiency`; datos sintéticos de 12 SKU |
| `checks/dq_01…11` | **Data Trust Gate**: 11 controles (consistencia, oportunidad, completitud, validez, unicidad); fila devuelta = falla |
| `lp_db/` | Adaptadores del agente (`PgPriority` con TTL, `PgSink` de auditoría) e `ingest_orders` (upsert parametrizado, commit/rollback) |
| `grafana/agent_kpis.json` | Panel de KPIs para Grafana |

## Contratos de datos (conexión con API-first)
El lakehouse es **consumidor** de `order.dispatched`, `trip.created` y `proposal.*` (`../../contracts/asyncapi/`). Un cambio incompatible en un evento rompe sus KPIs sin avisar: expliquen cómo tratarían el `schemaVersion`, la deduplicación por `eventId` (entrega al-menos-una-vez) y qué control de calidad añadirían. **Hoy no existe el consumidor**: es contrato, no código.

## Ponerlo a funcionar (15 min, con Docker)
```bash
make up && make lakehouse-data     # lakehouse con datos
make db-apply                      # aplica sql/10–15 (idempotentes: pueden repetirse)
make db-check                      # corre los 11 controles: deben decir OK
make test-bd                       # 11 pruebas (sintaxis con pglast; no requieren Docker)
```
Sin Docker: `make test-bd` valida estructura y sintaxis. **La semántica contra Postgres real la comprueba el CI (`ci-bd`) y ustedes con `make db-apply db-check`**; el docente no pudo ejecutarla.

## Qué deben exponer (12 min) — guion sugerido
1. **Modelo** (2 min): por qué `order_codes[]` viola 1FN y qué se gana con `proposal_stop`; por qué **no hay FK** a `master.customer` (el seed hace `TRUNCATE`) y cómo se compensa (DQ-01).
2. **Confianza** (3 min): las 5 dimensiones de calidad y qué control cubre cada una.
3. **Demo en vivo** (4 min): **rompan un dato a propósito** (p. ej. un cliente sin mapear o una propuesta vieja) y muestren qué control falla y por qué; ejecuten la prueba de privilegios.
4. **Análisis estratégico** (3 min): gobierno y valor (siguiente sección).

## Preguntas que debe poder responder el equipo
- ¿Por qué la auditoría es *append-only* y quién puede leerla? ¿Es suficiente para un auditor externo?
- `INSERT … ON CONFLICT (code) DO UPDATE`: ¿qué garantiza y qué **no** (p. ej. pedidos borrados en el lab)?
- Si DQ-04 falla (cliente sin prioridad), ¿el agente debe **detenerse**, degradarse (prioridad 1) o avisar? Defiendan su política y su costo.
- ¿Qué índice acelera `mart_agent.kpis` y cuándo convendría una vista materializada? ¿Cómo lo comprobarían (EXPLAIN)?
- ¿Qué KPI mostrarían a la gerencia? ¿Por qué la «tasa de aceptación» sola puede engañar?
- ¿Qué datos personales o comerciales hay en la auditoría y cuánto tiempo deben conservarse?

## Análisis estratégico — escenarios (elijan UNO)
- **A. Dato sucio.** El 15 % de los pedidos llega con cliente sin mapear. ¿Quién es dueño de arreglarlo, qué SLA, y qué hace el agente mientras tanto?
- **B. Valor.** La dirección duda del retorno del agente. Diseñen el tablero de 3 KPIs y la línea base contra la que se compara.
- **C. Lakehouse vs base transaccional única.** ¿Cuándo vale la complejidad del lakehouse para este caso y cuándo no? Costos de operación.
- **D. Cadena.** Un stock de inventario inflado hace que ~12 % de los pedidos no salgan completos. ¿Qué control añaden, quién es el dueño y cuánto vale evitarlo? (Hoy inventario, reposición y packing no tienen control propio.)

## Entregables y evaluación
Formato, rúbrica (30 puntos), defensa individual y declaración de uso de IA: **`../../docs/GUIA_EXPOSICION_Y_ANALISIS.md`** (común a todas las materias). Plantilla del análisis: `informe/PLANTILLA_ANALISIS.md`.

| Criterio | Pts | Qué miraremos específicamente en esta materia |
|---|---|---|
| Dominio técnico demostrado | 7,5 | Aplican SQL, ejecutan los controles, provocan una falla de calidad en vivo y la detectan; explican por qué `lp_agent` no puede borrar auditoría |
| Calidad del análisis estratégico | 9,0 | Gobierno del dato: dueños, qué bloquea al agente, KPI de valor (aceptación, fallback, uso de presupuesto) y costo de la mala calidad |
| Riesgos, gobernanza y límites | 4,5 | Qué cubre y qué NO cubre el Data Trust Gate; auditoría append-only; privacidad de datos de clientes |
| Conexión con Deber 3 | 3,0 | Nivel de autonomía recomendado y por qué; qué cambió respecto a la revisión de literatura |
| Exposición | 3,0 | 12 min exactos, un mensaje por diapositiva |
| Preguntas | 3,0 | Evidencia o «no lo sé, lo verificaría así» |

## Independencia
Este deber usa solo `base/` y su propia carpeta. Puede entregarse aunque los otros equipos no entreguen nada. Si quieren mostrar la integración, pueden activar su adaptador con la variable `LP_DATA_PLUGIN=lp_db.plugin:build y LP_AUDIT_PLUGIN=lp_db.plugin:build_sink` (opcional, no puntúa).
