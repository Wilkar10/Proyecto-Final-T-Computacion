# Resultados del laboratorio de decisión (SIMULACIÓN)

> **Lea esto primero.** Son resultados de un modelo con **supuestos ilustrativos** (`base/decision_lab/decision_lab/assumptions.json`), no datos de una operación real. Sirven para **comparar decisiones y entender qué mueve cada KPI**; no para afirmar «ahorramos X». Para afirmar ahorros hay que reemplazar los supuestos por datos medidos (p. ej. de DANEC) y repetir. Reproducir: `make decision-lab` (20 días, semilla 1; mismos pedidos para todas las políticas).

## Cómo leer las columnas
- **Despachos fallidos** = % de pedidos cuyo despacho falló, separado en *batería* (viaje abortado por mala estimación) y *error* (captura/duplicado/olvido o fallo de integración). 
- **SLA a tiempo** = % de pedidos entregados antes de su plazo (corporativo 120 min, PYME 180, minorista 240). **Sin entregar** = no salieron en 24 h.
- **Horas de planificación** = tiempo-persona de planificar (manual: por pedido; sistema: revisar/aprobar cada propuesta).
- **Costo/día** = movimiento + retrabajo por fallidos + penalidad por SLA incumplido + personal de planificación. **FTE liberados** = horas liberadas / 8.

> SIMULACIÓN con supuestos explícitos (decision_lab/assumptions.json). Los ahorros NO son reales hasta usar datos de operación.

### Escenario «normal»  (20 días simulados, semilla 1)

| Política | Despachos fallidos | SLA a tiempo | SLA corporativo | Sin entregar | Horas plan./día | Costo/día (USD) | Costo/pedido | Ahorro/mes vs manual | FTE liberados |
|---|---|---|---|---|---|---|---|---|---|
| manual_fifo | 19.2 % (15.7 bat. + 3.5 err.) | 98.2 % | 93.0 % | 0.0 % | 2.0 | 77 | 2.57 | +0 | 0.00 |
| sistema_prioridad | 0.5 % (0.0 bat. + 0.5 err.) | 99.8 % | 99.3 % | 0.0 % | 0.5 | 25 | 0.84 | +1,142 | 0.19 |
| sistema_cercania | 0.5 % (0.0 bat. + 0.5 err.) | 99.8 % | 99.3 % | 0.0 % | 0.5 | 25 | 0.84 | +1,142 | 0.19 |
| sistema_plazo | 0.5 % (0.0 bat. + 0.5 err.) | 99.8 % | 99.3 % | 0.0 % | 0.5 | 25 | 0.84 | +1,142 | 0.19 |
| sistema_plazo_heuristico | 0.5 % (0.0 bat. + 0.5 err.) | 100.0 % | 100.0 % | 0.0 % | 0.5 | 26 | 0.86 | +1,134 | 0.19 | 

### Escenario «pico»  (20 días simulados, semilla 1)

| Política | Despachos fallidos | SLA a tiempo | SLA corporativo | Sin entregar | Horas plan./día | Costo/día (USD) | Costo/pedido | Ahorro/mes vs manual | FTE liberados |
|---|---|---|---|---|---|---|---|---|---|
| manual_fifo | 25.4 % (22.0 bat. + 3.4 err.) | 90.0 % | 71.9 % | 0.0 % | 4.0 | 191 | 3.19 | +0 | 0.00 |
| sistema_prioridad | 0.4 % (0.0 bat. + 0.4 err.) | 99.7 % | 98.5 % | 0.0 % | 0.5 | 36 | 0.60 | +3,421 | 0.43 |
| sistema_cercania | 0.4 % (0.0 bat. + 0.4 err.) | 99.6 % | 98.2 % | 0.0 % | 0.5 | 36 | 0.60 | +3,422 | 0.43 |
| sistema_plazo | 0.4 % (0.0 bat. + 0.4 err.) | 99.7 % | 98.5 % | 0.0 % | 0.5 | 36 | 0.60 | +3,421 | 0.43 |
| sistema_plazo_heuristico | 0.4 % (0.0 bat. + 0.4 err.) | 99.8 % | 99.3 % | 0.0 % | 0.5 | 37 | 0.61 | +3,401 | 0.43 | 

### Escenario «flota_reducida»  (20 días simulados, semilla 1)

| Política | Despachos fallidos | SLA a tiempo | SLA corporativo | Sin entregar | Horas plan./día | Costo/día (USD) | Costo/pedido | Ahorro/mes vs manual | FTE liberados |
|---|---|---|---|---|---|---|---|---|---|
| manual_fifo | 14.7 % (11.2 bat. + 3.5 err.) | 93.8 % | 79.6 % | 0.0 % | 2.0 | 73 | 2.43 | +0 | 0.00 |
| sistema_prioridad | 0.5 % (0.0 bat. + 0.5 err.) | 98.3 % | 93.7 % | 0.0 % | 0.4 | 26 | 0.85 | +1,042 | 0.20 |
| sistema_cercania | 0.5 % (0.0 bat. + 0.5 err.) | 98.8 % | 95.1 % | 0.0 % | 0.4 | 25 | 0.83 | +1,056 | 0.20 |
| sistema_plazo | 0.5 % (0.0 bat. + 0.5 err.) | 98.3 % | 93.7 % | 0.0 % | 0.4 | 26 | 0.85 | +1,042 | 0.20 |
| sistema_plazo_heuristico | 0.5 % (0.0 bat. + 0.5 err.) | 99.2 % | 97.2 % | 0.0 % | 0.4 | 25 | 0.84 | +1,052 | 0.20 | 

### Escenario «manual_sin_errores»  (20 días simulados, semilla 1)

| Política | Despachos fallidos | SLA a tiempo | SLA corporativo | Sin entregar | Horas plan./día | Costo/día (USD) | Costo/pedido | Ahorro/mes vs manual | FTE liberados |
|---|---|---|---|---|---|---|---|---|---|
| manual_fifo | 0.0 % (0.0 bat. + 0.0 err.) | 99.8 % | 99.3 % | 0.0 % | 2.0 | 38 | 1.27 | +0 | 0.00 |
| sistema_prioridad | 0.5 % (0.0 bat. + 0.5 err.) | 99.8 % | 99.3 % | 0.0 % | 0.5 | 25 | 0.84 | +285 | 0.19 |
| sistema_cercania | 0.5 % (0.0 bat. + 0.5 err.) | 99.8 % | 99.3 % | 0.0 % | 0.5 | 25 | 0.84 | +284 | 0.19 |
| sistema_plazo | 0.5 % (0.0 bat. + 0.5 err.) | 99.8 % | 99.3 % | 0.0 % | 0.5 | 25 | 0.84 | +285 | 0.19 |
| sistema_plazo_heuristico | 0.5 % (0.0 bat. + 0.5 err.) | 100.0 % | 100.0 % | 0.0 % | 0.5 | 26 | 0.86 | +276 | 0.19 | 



## Nivel de autonomía: ¿aprobar cada viaje (nivel 1) o solo los riesgosos (nivel 2)?
Generado con `make autonomia` (misma política `sistema_plazo` y mismos pedidos; solo cambia quién aprueba). **Supuestos ilustrativos** en el bloque `autonomy` de `assumptions.json`: una aprobación demora 20 min y cuesta 3 min-persona, la persona atrapa el 50 % de los errores, y en nivel 2 salen sin aprobar los viajes de hasta 3 paradas, sin pedidos corporativos y con 10 puntos de batería de sobra.

### Autonomía · escenario «normal»  (20 días simulados, semilla 1)

| Caso | Despachos fallidos | SLA a tiempo | SLA corporativo | Aprobaciones/día | Viajes sin aprobar | Horas-persona/día | Costo/día (USD) | Ahorro/mes vs manual |
|---|---|---|---|---|---|---|---|---|
| manual_fifo | 19.17 % | 98.2 % | 93.0 % | 0.0 | 0 % | 2.00 | 77 | +0 |
| sistema_plazo · nivel 1 | 0.33 % | 99.7 % | 98.6 % | 13.6 | 0 % | 1.13 | 30 | +1,032 |
| sistema_plazo · nivel 2 | 0.50 % | 99.7 % | 98.6 % | 7.7 | 43 % | 0.84 | 28 | +1,078 | 

### Autonomía · escenario «pico»  (20 días simulados, semilla 1)

| Caso | Despachos fallidos | SLA a tiempo | SLA corporativo | Aprobaciones/día | Viajes sin aprobar | Horas-persona/día | Costo/día (USD) | Ahorro/mes vs manual |
|---|---|---|---|---|---|---|---|---|
| manual_fifo | 25.42 % | 90.0 % | 71.9 % | 0.0 | 0 % | 4.00 | 191 | +0 |
| sistema_plazo · nivel 1 | 0.25 % | 98.2 % | 93.1 % | 16.0 | 0 % | 1.33 | 44 | +3,241 |
| sistema_plazo · nivel 2 | 0.25 % | 98.6 % | 93.8 % | 12.4 | 23 % | 1.16 | 42 | +3,289 | 

### Autonomía · escenario «flota_reducida»  (20 días simulados, semilla 1)

| Caso | Despachos fallidos | SLA a tiempo | SLA corporativo | Aprobaciones/día | Viajes sin aprobar | Horas-persona/día | Costo/día (USD) | Ahorro/mes vs manual |
|---|---|---|---|---|---|---|---|---|
| manual_fifo | 14.67 % | 93.8 % | 79.6 % | 0.0 | 0 % | 2.00 | 73 | +0 |
| sistema_plazo · nivel 1 | 0.33 % | 97.7 % | 91.5 % | 11.7 | 0 % | 0.97 | 29 | +963 |
| sistema_plazo · nivel 2 | 0.50 % | 97.3 % | 89.4 % | 7.1 | 42 % | 0.76 | 29 | +974 | 

### Autonomía · escenario «manual_sin_errores»  (20 días simulados, semilla 1)

| Caso | Despachos fallidos | SLA a tiempo | SLA corporativo | Aprobaciones/día | Viajes sin aprobar | Horas-persona/día | Costo/día (USD) | Ahorro/mes vs manual |
|---|---|---|---|---|---|---|---|---|
| manual_fifo | 0.00 % | 99.8 % | 99.3 % | 0.0 | 0 % | 2.00 | 38 | +0 |
| sistema_plazo · nivel 1 | 0.33 % | 99.7 % | 98.6 % | 13.6 | 0 % | 1.13 | 30 | +174 |
| sistema_plazo · nivel 2 | 0.50 % | 99.7 % | 98.6 % | 7.7 | 43 % | 0.84 | 28 | +220 |

**Lectura gerencial (con esos supuestos; cámbienlos y vuelvan a correr):**
- El salto grande está entre manual y sistema (fallidos de ~19 % a ~0,3-0,5 %). Pasar del nivel 1 al 2 mueve poco el costo (unos +50 USD/mes en «normal») y libera ~0,3 horas-persona por día.
- El nivel 2 **no sale gratis**: sube un poco los despachos fallidos (los errores de los viajes sin aprobar ya no los atrapa nadie) y, con **flota reducida**, el SLA corporativo empeora (≈ 91,5 % → 89,4 %) porque los viajes riesgosos siguen esperando aprobación mientras los demás compiten por pocos robots.
- Por tanto la pregunta no es «¿se puede?», sino: *¿cuánto vale una hora de aprobador frente al costo de un despacho fallido sin revisar?* Con otro `human_catch_rate` o `approval_delay_min` la respuesta cambia: ahí está el análisis.
- **Límite:** es un modelo; no mide el riesgo de un error grave y raro (el que justifica el control humano), solo el promedio de errores pequeños.

## Cadena completa: inventario → pedidos → reposición → packing → despacho
Generado con `make cadena`. Se mejora **una etapa a la vez** (misma demanda en todas las filas) para ver qué aporta cada una. **Supuestos ilustrativos** en el bloque `cadena` de `assumptions.json`: 12 SKU, pronóstico manual sesgado −25 %, revisión manual cada 5 días, plazo de reposición 2 días, caja de capacidad 10, errores y tiempos de empaque. *Fallidos totales* = falta de producto + error de empaque + fallidos de despacho.

#### Cadena completa · escenario «normal»  (20 días simulados, semilla 1)

| Paso | Falta de producto | Error de empaque | Fallidos de despacho | **Fallidos totales** | SLA a tiempo | Cajas/pedido (llenado) | Cobertura (días) | Horas-persona/día | Costo/día (USD) | Ahorro/mes vs manual |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 · todo manual | 12.0 % | 2.3 % | 16.7 % | **31.0 %** | 84.8 % | 1.62 (68 %) | 2.5 | 5.0 | 166 | +0 |
| 1 · + reposición con punto de pedido | 0.2 % | 3.0 % | 22.0 % | **25.2 %** | 96.0 % | 1.65 (69 %) | 3.7 | 5.7 | 156 | +214 |
| 2 · + packing optimizado | 0.2 % | 1.0 % | 23.5 % | **24.7 %** | 96.3 % | 1.64 (69 %) | 3.7 | 3.8 | 145 | +448 |
| 3 · + despacho optimizado | 0.2 % | 1.0 % | 0.5 % | **1.7 %** | 99.7 % | 1.64 (69 %) | 3.7 | 2.3 | 83 | +1,811 |

Costo/día por componente (USD): movimiento 20.6 · retrabajo 0.9 · penalidad_sla 0.4 · personal_planificacion 3.5 · inventario 16.5 · compras 13.8 · empaque 26.8 · reposicion_personal 0.3 · quiebres 0.4  (último paso) 

#### Cadena completa · escenario «pico»  (20 días simulados, semilla 1)

| Paso | Falta de producto | Error de empaque | Fallidos de despacho | **Fallidos totales** | SLA a tiempo | Cajas/pedido (llenado) | Cobertura (días) | Horas-persona/día | Costo/día (USD) | Ahorro/mes vs manual |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 · todo manual | 10.2 % | 2.3 % | 25.3 % | **37.8 %** | 78.1 % | 1.59 (68 %) | 2.4 | 10.1 | 359 | +0 |
| 1 · + reposición con punto de pedido | 0.0 % | 2.8 % | 29.2 % | **32.1 %** | 85.2 % | 1.61 (68 %) | 3.6 | 11.3 | 343 | +361 |
| 2 · + packing optimizado | 0.0 % | 0.8 % | 27.1 % | **27.9 %** | 88.2 % | 1.60 (69 %) | 3.6 | 7.5 | 302 | +1,252 |
| 3 · + despacho optimizado | 0.0 % | 0.8 % | 0.4 % | **1.2 %** | 99.6 % | 1.60 (69 %) | 3.6 | 4.0 | 137 | +4,894 |

Costo/día por componente (USD): movimiento 29.6 · retrabajo 1.5 · penalidad_sla 1.0 · personal_planificacion 4.2 · inventario 32.7 · compras 15.2 · empaque 51.9 · reposicion_personal 0.4 · quiebres 0.0  (último paso) 

#### Cadena completa · escenario «flota_reducida»  (20 días simulados, semilla 1)

| Paso | Falta de producto | Error de empaque | Fallidos de despacho | **Fallidos totales** | SLA a tiempo | Cajas/pedido (llenado) | Cobertura (días) | Horas-persona/día | Costo/día (USD) | Ahorro/mes vs manual |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 · todo manual | 12.0 % | 2.3 % | 17.2 % | **31.5 %** | 80.0 % | 1.62 (68 %) | 2.5 | 5.0 | 171 | +0 |
| 1 · + reposición con punto de pedido | 0.2 % | 3.0 % | 19.3 % | **22.5 %** | 90.5 % | 1.65 (69 %) | 3.7 | 5.7 | 156 | +329 |
| 2 · + packing optimizado | 0.2 % | 1.0 % | 18.5 % | **19.7 %** | 92.8 % | 1.64 (69 %) | 3.7 | 3.8 | 139 | +699 |
| 3 · + despacho optimizado | 0.2 % | 1.0 % | 0.5 % | **1.7 %** | 98.7 % | 1.64 (69 %) | 3.7 | 2.2 | 83 | +1,926 |

Costo/día por componente (USD): movimiento 19.5 · retrabajo 0.9 · penalidad_sla 1.6 · personal_planificacion 3.3 · inventario 16.5 · compras 13.8 · empaque 26.8 · reposicion_personal 0.3 · quiebres 0.4  (último paso) 

#### Cadena completa · escenario «manual_sin_errores»  (20 días simulados, semilla 1)

| Paso | Falta de producto | Error de empaque | Fallidos de despacho | **Fallidos totales** | SLA a tiempo | Cajas/pedido (llenado) | Cobertura (días) | Horas-persona/día | Costo/día (USD) | Ahorro/mes vs manual |
|---|---|---|---|---|---|---|---|---|---|---|
| 0 · todo manual | 12.0 % | 2.3 % | 0.0 % | **14.3 %** | 87.0 % | 1.62 (68 %) | 2.5 | 5.0 | 131 | +0 |
| 1 · + reposición con punto de pedido | 0.2 % | 3.0 % | 0.0 % | **3.2 %** | 98.2 % | 1.65 (69 %) | 3.7 | 5.7 | 111 | +439 |
| 2 · + packing optimizado | 0.2 % | 1.0 % | 0.0 % | **1.2 %** | 99.2 % | 1.64 (69 %) | 3.7 | 3.8 | 97 | +744 |
| 3 · + despacho optimizado | 0.2 % | 1.0 % | 0.5 % | **1.7 %** | 99.7 % | 1.64 (69 %) | 3.7 | 2.3 | 83 | +1,045 |

Costo/día por componente (USD): movimiento 20.6 · retrabajo 0.9 · penalidad_sla 0.4 · personal_planificacion 3.5 · inventario 16.5 · compras 13.8 · empaque 26.8 · reposicion_personal 0.3 · quiebres 0.4  (último paso) 


**Lectura gerencial (con esos supuestos):**
- **Reposición:** con pronóstico sesgado y revisión cada 5 días, ~12 % de los pedidos no sale completo. Un punto de pedido con demanda observada lo baja a ~0,2 % y sube la cobertura de ~2,5 a ~3,7 días de inventario: compra más seguido y mantiene más stock, y aun así el costo total baja. Si el comprador manual no tuviera sesgo y revisara a diario, esa ventaja casi desaparece (hay una prueba que lo muestra): el beneficio depende de ese supuesto, no es una ley.
- **Packing:** optimizar el acomodo (first-fit decreasing) casi no cambia las cajas por pedido (≈ 1,65 → 1,64; el llenado ronda 69 %). Lo que ahorra son las horas y los errores supuestos de empaque. Antes de invertir en un algoritmo, midan cuántas cajas y cuánto tiempo gasta hoy el empaque real.
- **Despacho:** es la etapa de mayor impacto en fallidos y SLA *en este modelo* porque el despacho manual subestima baterías. Si el despachador no se equivoca (escenario «manual_sin_errores»), el aporte baja y el de la reposición domina.
- **Interacción:** cuando la reposición mejora, el despacho manual recibe más pedidos y sus fallos suben (16,7 % → 22 %): resolver una etapa puede destapar el cuello de botella de la siguiente. Por eso se mira *fallidos totales* y no una etapa aislada.
- **Límite:** un solo almacén, plazo de reposición fijo, sin lotes mínimos ni vencimientos, empaque con operarios ilimitados, y los pedidos incompletos no se reponen después (se cuentan como fallidos). Es un modelo para decidir dónde mirar, no para prometer ahorros.

## Qué enseñan estos números (lectura gerencial)
1. **La mayor parte del beneficio viene de eliminar errores y escalar, no de optimizar la ruta.** Con un despachador manual *sin* errores (`manual_sin_errores`) el ahorro cae a ~USD 285/mes frente a ~USD 1.100 con los errores supuestos. Quien promete ahorros por «rutas óptimas» está sobreestimando; el valor está en **cero despachos abortados, idempotencia y trazabilidad**.
2. **Bajo presión, el manual se rompe primero.** En `pico` (60 pedidos/día) el SLA corporativo manual cae a ~72 % mientras el sistema se mantiene sobre 98 %; las horas de planificación se duplican.
3. **Optimizar el objetivo equivocado no ayuda.** El recorrido exacto minimiza *costo de ruta*, no *retraso*; en `flota_reducida` la variante heurística obtuvo mejor SLA (97,2 % vs 93,7 % corporativo). La pregunta de negocio es **qué objetivo se optimiza** (costo, plazo, prioridad por cliente), no solo si el algoritmo es exacto.
4. **Con flota holgada las políticas casi empatan**; diferencian cuando la capacidad escasea (`flota_reducida`). Decisión estratégica: ¿invertir en optimización o en más flota? Este modelo permite probar ambas palancas.
5. **El sistema no tiene fallos cero:** se supone 0,5 % de error residual (integración). Si esa cifra real fuese 5 %, parte del ahorro desaparece: es un **dato crítico a medir**.

## Qué NO cubre el modelo (límites)
Una sola bodega y plano pequeño; llegada uniforme de pedidos; sin tráfico real, devoluciones ni cambios de última hora; costos y tasas de error inventados; sin costo de implantar, mantener ni capacitar (el ahorro es **bruto**, no neto); un solo semilla (haga sensibilidad variando `--seed` y los supuestos).
