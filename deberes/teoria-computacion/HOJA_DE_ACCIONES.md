# Hoja de acciones — Teoría de la Computación (1 página)

**Su rol:** gerente de decisión. Todo está configurado; ustedes ejecutan, miran la evidencia y **deciden**.

## Pasos (≈ 30 min)
| # | Acción | Comando | Deben ver |
|---|---|---|---|
| 1 | Verificar que todo funciona | `make test-teoria` | 186 pruebas en verde |
| 2 | Ver cuánto crece el costo de la ruta exacta | `cd deberes/teoria-computacion && python -m np_lab.bench tsp 6 7 8 9 10 11 12` | tabla: el tiempo exacto se dispara; la heurística no |
| 3 | Ver el efecto en el negocio | `make decision-lab` | tabla de fallidos, SLA, costo y horas-persona |
| 4 | Elegir nivel de autonomía | `make autonomia` | tabla nivel 1 vs nivel 2 (`docs/RESULTADOS_LAB_DECISION.md`) |
| 5 | Elegir UN escenario (A, B o C) del README y responderlo en `informe/PLANTILLA_ANALISIS.md` | — | informe de ≤ 3 páginas |

**La cadena completa** (inventario → pedidos → reposición → packing → delivery): `make cadena` muestra qué aporta cada etapa en falta de producto, error de empaque, fallidos, SLA y costo. Es simulación con supuestos; el escenario «Cadena» del README la usa.

## Decisiones que deben defender (con una cifra de la evidencia cada una)
1. **¿Exacto o heurístico, y hasta qué tamaño de viaje?** Fijen el umbral de paradas donde cambian de método y su justificación en tiempo vs calidad.
2. **¿Qué garantía pueden prometer a un cliente?** (escenario B): redacten la cláusula.
3. **Autonomía: nivel 1 (default) o nivel 2.** Citen aprobaciones/día, horas-persona liberadas, y el costo en despachos fallidos y SLA corporativo. Nivel 1 es el punto de partida; el 2 es una propuesta que deben sostener con KPIs.

## Entrega
Informe + 12 min de exposición. No se evalúa programar: se evalúa la calidad de la decisión y qué dato real la confirmaría.
