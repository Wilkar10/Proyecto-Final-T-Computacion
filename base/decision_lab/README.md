# Laboratorio de decisión · ¿mejora el sistema los KPIs de negocio?

Simula días de operación con **los mismos pedidos** bajo distintas políticas y mide lo que importa a la gerencia:
**despachos fallidos · cumplimiento de SLA (también por segmento) · costo por pedido · horas-persona de planificación · ahorro mensual**.

| Política | Qué representa |
|---|---|
| `manual_fifo` | **Línea base**: un despachador agrupa los pedidos más antiguos (hasta 4), no optimiza el recorrido y a veces subestima el costo o se equivoca |
| `sistema_prioridad` / `sistema_cercania` / `sistema_plazo` | El sistema arma viajes con recorrido **óptimo** (Held-Karp) y el **validador** impide despachar lo inviable; cambia el criterio de selección |
| `sistema_plazo_heuristico` | Igual que `sistema_plazo` pero con vecino más cercano (sin óptimo): mide cuánto vale (o no) la exactitud |

```bash
make decision-lab                                                     # 4 escenarios: normal, pico, flota_reducida, manual_sin_errores
PYTHONPATH=base/agent:base/decision_lab python -m decision_lab.run --scenario pico --days 30 --seed 7
```
```bash
make autonomia          # nivel 1 (una persona aprueba cada viaje) vs nivel 2 (solo lo riesgoso), con los mismos pedidos
```
**Cambiar supuestos:** edite `decision_lab/assumptions.json` o pase `--assumptions mi_archivo.json`. **Todos los valores son supuestos ilustrativos**; los resultados se leen en `docs/RESULTADOS_LAB_DECISION.md`.

> Es una simulación para *comparar decisiones*. No demuestra ahorros reales: para eso hay que reemplazar los supuestos por datos medidos de la operación y restar el costo de implantar y mantener el sistema.

## Contraste con datos públicos de referencia (`refdata/`)
Los supuestos de `assumptions.json` se pueden **contrastar** (no reemplazar) con datos públicos:
- **Olist** (Kaggle `olistbr/brazilian-ecommerce`, marketplace real de Brasil): % de entregas tardías contra la fecha prometida, cancelaciones, flete y variación por región.
- **Corporación Favorita** (Kaggle `store-sales-time-series-forecasting`, retailer de Ecuador): forma de la demanda (pico sobre la media, índice por día de la semana).
```bash
make contraste OLIST=datos/olist FAVORITA=datos/favorita     # escribe docs/CONTRASTE_SUPUESTOS.md
```
**Límites:** no son datos de DANEC; Olist es e-commerce con plazos de días y Favorita es demanda, no despacho. **Los cargadores no se han probado con los archivos reales** (sin acceso a Kaggle desde donde se construyó): se verifican con archivos mínimos que respetan el esquema documentado. La primera ejecución real es parte del trabajo. Para sustituir los supuestos por cifras de DANEC: `docs/SOLICITUD_DATOS_DANEC.md`.

## Cadena completa (`make cadena`)
`decision_lab/cadena.py` modela inventario → pedidos → reposición → packing; el despacho sigue en `sim.py`. `python -m decision_lab.run --cadena` mejora una etapa a la vez y muestra falta de producto, error de empaque, fallidos de despacho, SLA, cajas por pedido, cobertura, horas-persona y costo. Los supuestos están en el bloque `cadena` de `assumptions.json`. Resultados y lectura en `docs/RESULTADOS_LAB_DECISION.md`.
