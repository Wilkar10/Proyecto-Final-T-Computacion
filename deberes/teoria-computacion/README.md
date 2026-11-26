# Proyecto final · Teoría de la Computación — «El agente propone, el verificador decide»

> **Empiecen por `HOJA_DE_ACCIONES.md`** (1 página): pasos exactos, qué deben ver y las decisiones a defender.

**Qué es:** la pieza de Teoría del proyecto final LOGISTPULSE, **ya implementada y probada** (186 pruebas verdes). Su trabajo es **entenderla, ejecutarla, exponerla y decidir con criterio estratégico** cuánta garantía puede prometer el negocio. Es independiente de los otros deberes.

**Dónde se conecta:** el agente de despacho elige un robot y varios pedidos; el orden de las paradas es **TSP en versión de decisión** (¿existe un ciclo que visite todas las paradas con costo ≤ batería − reserva?), problema **NP-completo**. La matriz de costos sale de Dijkstra sobre la grilla (clase **P**).

```
 agente (LLM o reglas) ──elige pedidos──▶ SOLVER (np_lab/plugin.py) ──tour + costo──▶ VERIFICADOR V (polinomial) ──▶ propuesta pendiente
```

## Su aporte a los KPI de negocio
**KPI que mueve:** costo por pedido (distancia/batería) y capacidad (cuántos pedidos caben por viaje).
**Evidencia del lab de decisión** (`docs/RESULTADOS_LAB_DECISION.md`): el recorrido **óptimo** vs el heurístico cambia el costo apenas en este tamaño (≈ USD 8/mes en el escenario normal) y, con flota reducida, la variante heurística incluso cumplió mejor el SLA corporativo (97,2 % vs 93,7 %): **minimizar distancia no es minimizar retraso**. Su análisis debe responder: ¿cuánto vale la garantía de optimalidad, hasta qué tamaño de operación, y **qué objetivo** (costo, plazo, prioridad) conviene optimizar?

## Qué contiene (todo implementado)
| Ruta | Qué hay |
|---|---|
| `np_lab/tsp.py` | Fuerza bruta, **Held-Karp** (DP por subconjuntos con reconstrucción), vecino más cercano, **2-opt**, verificador del certificado |
| `np_lab/sat.py` | Verificador SAT y **DPLL** (propagación unitaria + ramificación) |
| `np_lab/vertex_cover.py` | Verificador y **2-aproximación** (emparejamiento maximal) |
| `np_lab/plugin.py` | **Política de selección**: n ≤ 8 fuerza bruta · n ≤ 15 Held-Karp · si no, NN + 2-opt (`proven=False`) |
| `np_lab/bench.py` | Medición con límite de tiempo en proceso aparte |
| `docs/RESULTADOS_BENCHMARK.md` | **Resultados medidos** (fuerza bruta: 4,4 s a n=10, > 10 s a n=11; Held-Karp: 0,04 s a n=12) |
| `simulador/` | Simulador P/NP/NP-completo (HTML): casos p1–p3, n1–n4, c1–c3 |
| `np_lab/logistica.py` | **Mochila** (fuerza bruta, DP pseudo-polinomial, voraz) · **empaque** (FFD vs exacto) · **cobertura** (voraz vs exacto) · **asignación a varios robots** · **recorrido con plazos** (EDF vs DP) · todos con su verificador |
| `np_lab/datos.py` · `supuestos_teoria.json` | Lee pedidos, pesos, plazos y cobertura del **lakehouse** (Postgres); si no está, usa datos de **ejemplo** y lo avisa. Supuestos declarados: coordenadas, capacidades, margen de plazo |
| `np_lab/registro.py` | Registra cada corrida y la guarda en `teoria.solver_run` (Postgres) y en el Data Lake (CSV en MinIO) |
| `notebooks/02_teoria_sobre_el_lakehouse.ipynb` | **El análisis**: cada problema con su clase, certificado, algoritmo exacto, heurística, tamaño medido y lectura gerencial |
| `grafana/teoria_solver.json` | Tablero (importar en Grafana): corridas, brecha de heurísticas, tiempos |

## Análisis en JupyterLab sobre el lakehouse
```bash
make up-lakehouse && make lakehouse-data     # Postgres + MinIO + Grafana con datos
make lab-teoria                              # JupyterLab en :8888 → carpeta «teoria» → 02_teoria_sobre_el_lakehouse
make db-teoria                               # solo si el lakehouse ya existía antes de este cambio (crea teoria.solver_run)
```
El notebook usa los pedidos pendientes reales (`ods.orders` en `CREATED`) del depósito con más pendientes. Sin lakehouse corre igual con **datos de ejemplo** y lo imprime en la primera celda. Al final guarda las corridas; en Grafana, **Dashboards → Import** `grafana/teoria_solver.json`.
**Límites:** el lakehouse es sintético (`lp.seed`); la base no tiene coordenadas ni capacidades de carga (son **supuestos** en `supuestos_teoria.json`); las consultas SQL se validaron por sintaxis, **no se han ejecutado contra un Postgres real**, y el notebook solo se ejecutó con los datos de ejemplo.

## Ponerlo a funcionar (10 min)
```bash
make test-teoria                                      # 186 pruebas
cd deberes/teoria-computacion && python -m np_lab.bench tsp 6 7 8 9 10 11 12   # reproduzcan la tabla
make agent-local LP_SOLVER_PLUGIN=np_lab.plugin:build # el agente usa SU solver
```

## Qué deben exponer (12 min) — guion sugerido
1. **El problema** (2 min): del negocio (¿cuántos pedidos le caben a un robot?) a TSP-decisión; por qué el cálculo de rutas es P y el recorrido es NP-completo.
2. **Certificado y verificador** (2 min): qué es el certificado, por qué V es polinomial, por qué el agente nunca confía en el solver sin V.
3. **Demo en vivo** (4 min): corran el benchmark, **cambien n o la semilla y predigan** el resultado; muestren una instancia donde NN pierde contra Held-Karp.
4. **Análisis estratégico** (3 min): su recomendación (sección siguiente).
5. **Límites** (1 min): qué no garantiza el sistema.

## Preguntas que debe poder responder el equipo
- ¿Por qué la mochila es NP-completa y aun así su DP fue rápida? ¿Qué cambia al medir el peso en gramos? (pseudo-polinomial)
- ¿Por qué la ruta de mínima distancia puede incumplir plazos y cuánto cuesta cumplirlos?
- Empaque: ¿qué dice la cota FFD ≤ 11/9·OPT + 6/9 que no diga la heurística de asignación a robots?
- ¿Por qué Held-Karp sigue siendo exponencial y aun así sirve aquí? ¿Hasta qué n y por qué `MAX_STOPS = 12` lo vuelve práctico?
- Si 2-opt responde «no hay ciclo ≤ presupuesto», ¿es una prueba? ¿Qué debe hacer el agente?
- ¿Qué cambia si el problema real fuera *asignar pedidos a robots* (varios vehículos)? ¿A qué problema NP-completo se parece?
- ¿Para qué sirve DPLL/Vertex Cover en una empresa logística? ¿Dónde aparece SAT en la práctica (reglas de configuración, compatibilidad)?
- ¿Por qué no se puede automatizar «verificar que cualquier agente cumple una propiedad semántica no trivial» (Rice)? ¿Qué hacemos entonces (validador sobre la *salida*)?
- El benchmark es una sola semilla y una máquina: ¿qué le añadirían para que sea evidencia seria?

## Análisis estratégico — escenarios (elijan UNO y respóndanlo en su informe)
- **A. Crecimiento.** La flota crece 10 × y los viajes pasan de 8 a 40 paradas. ¿Qué cambia en la política de selección, qué calidad de solución prometen y cuánto cuesta?
- **B. Garantía contractual.** Un cliente exige «ruta óptima garantizada». ¿Pueden prometerlo? ¿Con qué condiciones de tamaño y tiempo? ¿Qué cláusula propondrían?
- **C. Comprar vs construir.** Un proveedor ofrece un servicio de optimización de rutas. Criterios de decisión, costo de salida y qué conservarían (el validador V).
- **D. Cadena.** Con `make cadena`, ¿en qué etapa invierten primero para bajar los fallidos totales y qué problema de la computación respalda su elección?

## Entregables y evaluación
Formato, rúbrica (30 puntos), defensa individual y declaración de uso de IA: **`../../docs/GUIA_EXPOSICION_Y_ANALISIS.md`** (común a todas las materias). Plantilla del análisis: `informe/PLANTILLA_ANALISIS.md`.

| Criterio | Pts | Qué miraremos específicamente en esta materia |
|---|---|---|
| Dominio técnico demostrado | 7,5 | Corren `bench`, cambian n o la semilla en vivo y **predicen** qué algoritmo gana y con qué costo; explican Held-Karp (O(n²·2ⁿ)) y DPLL sin leer |
| Calidad del análisis estratégico | 9,0 | Estrategia exacta vs heurística vs solver externo con costos, y su decisión sobre garantías al negocio |
| Riesgos, gobernanza y límites | 4,5 | Qué significa un «no» de la heurística (`proven=False`), por qué V es polinomial, dónde termina la garantía |
| Conexión con Deber 3 | 3,0 | Nivel de autonomía recomendado y por qué; qué cambió respecto a la revisión de literatura |
| Exposición | 3,0 | 12 min exactos, un mensaje por diapositiva |
| Preguntas | 3,0 | Evidencia o «no lo sé, lo verificaría así» |

## Independencia
Este deber usa solo `base/` y su propia carpeta. Puede entregarse aunque los otros equipos no entreguen nada. Si quieren mostrar la integración, pueden activar su adaptador con la variable `LP_SOLVER_PLUGIN=np_lab.plugin:build` (opcional, no puntúa).
