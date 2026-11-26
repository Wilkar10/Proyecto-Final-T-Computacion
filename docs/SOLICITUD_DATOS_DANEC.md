# Solicitud de datos para la visita técnica a DANEC

**Para qué:** reemplazar los supuestos de `base/decision_lab/decision_lab/assumptions.json` por cifras reales, de modo que los ahorros (despachos fallidos, SLA, costo y personal) dejen de ser simulados. Cada fila de la tabla indica **qué parámetro del laboratorio cambia**.

**Condiciones sugeridas:** datos **anonimizados** (códigos en lugar de nombres de clientes), agregados por semana o mes si el detalle es sensible, periodo de **al menos 3 meses**, con la **unidad y la definición** de cada cifra. Nada de esto debe subirse a un repositorio público sin autorización de DANEC.

## A. Mínimo indispensable (una hoja)
| # | Dato | Definición pedida | Parámetro que reemplaza |
|---|---|---|---|
| 1 | Pedidos despachados por día | Promedio, mínimo y máximo (y del día más cargado del mes) | `orders_per_day`, escenario `pico` |
| 2 | Mezcla de clientes | % de pedidos y de volumen por tipo (p. ej. mayorista, supermercado, institucional) | `segments.*.share` |
| 3 | Promesa de servicio | Plazo acordado por tipo de cliente (horas o días) y cómo se mide el cumplimiento | `segments.*.sla_min` |
| 4 | % de pedidos entregados dentro del plazo | Por tipo de cliente, últimos 3 meses | Línea base del SLA |
| 5 | % de despachos fallidos y su causa | Fallido = pedido que no sale/llega completo y a tiempo. Causas: error de captura, falta de producto, vehículo, otro | `manual.error_rate` |
| 6 | Costo por entrega | Combustible, transportista y peaje por viaje o por pedido (USD) | `money.cost_per_cost_unit_usd` |
| 7 | Costo de un despacho fallido | Reproceso, devolución, penalidad contractual (USD por pedido) | `money.rework_cost_per_failed_order_usd`, `late_penalty_per_order_usd` |
| 8 | Personal que planifica despachos | Personas y horas por día dedicadas a armar rutas/asignar | `manual.plan_min_per_order`, `money.planner_hourly_usd` |
| 9 | Flota | Unidades disponibles por día y cuántas paradas hace un viaje típico | `robots`, `manual.group_size` |

## B. Si es posible (pedidos con detalle)
Una fila por pedido, sin datos personales, con las columnas de `docs/plantillas/pedidos_danec.csv`: fecha/hora de pedido, fecha prometida, fecha real de entrega, tipo de cliente (código), zona, peso o volumen, unidad de transporte, estado final, motivo si falló, costo de entrega.

## C. Preguntas para la conversación (no son datos)
1. ¿Quién decide hoy qué se despacha primero y con qué criterio? ¿Está escrito?
2. ¿Qué pasa cuando un despacho falla: quién se entera, cuánto tarda y qué se registra?
3. ¿Qué decisión de logística tomarían distinto si tuvieran el dato en línea?
4. ¿Qué parte de la planificación se hace en hojas de cálculo o de memoria?

## D. Qué haremos con los datos
Correr `python -m decision_lab.run --assumptions danec.json`, comparar el resultado con el contraste de datos públicos (`make contraste`) y presentar a DANEC un tablero de KPIs con **qué dato falta** para cada conclusión. Los equipos deben declarar qué supuestos siguen sin respaldo.
