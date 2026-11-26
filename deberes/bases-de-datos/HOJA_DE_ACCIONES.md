# Hoja de acciones — Bases de Datos (1 página)

**Su rol:** dueños del dato y del tablero. El esquema, los controles y los datos de ejemplo ya vienen listos.

## Pasos (≈ 30 min, con Docker)
| # | Acción | Comando | Deben ver |
|---|---|---|---|
| 1 | Levantar con datos | `make up && make lakehouse-data` | servicios arriba; lakehouse con datos |
| 2 | Aplicar el esquema | `make db-apply` | sin errores (se puede repetir) |
| 3 | Pasar el Data Trust Gate | `make db-check` | los 11 controles dicen OK |
| 4 | Abrir el tablero | Grafana http://localhost:3000 | los 3 KPIs sobre datos |
| 5 | Ver el nivel de autonomía | `make autonomia` | tabla nivel 1 vs nivel 2 |
| 6 | Elegir UN escenario (A, B o C) y responderlo en `informe/PLANTILLA_ANALISIS.md` | — | informe |

Sin Docker: `make test-bd` (11 pruebas) valida estructura y sintaxis; la semántica contra Postgres real la confirma el CI o el paso 3.

**La cadena completa** (inventario → pedidos → reposición → packing → delivery): `make cadena` muestra qué aporta cada etapa en falta de producto, error de empaque, fallidos, SLA y costo. Es simulación con supuestos; el escenario «Cadena» del README la usa.

## Decisiones que deben defender
1. **Confiabilidad del dato:** si un control falla, ¿se bloquea la decisión del agente o se avisa? ¿Quién es el dueño y con qué SLA?
2. **Línea base:** ¿contra qué cifra comparan los 3 KPIs (despachos fallidos, SLA, horas-persona)?
3. **Autonomía 1 o 2:** ¿qué dato necesita el nivel 2 para ser seguro (p. ej. % de aprobaciones corregidas por la persona) y qué umbral los haría volver al nivel 1?

## Entrega
Informe + 12 min de exposición. Se evalúa el criterio de gobierno del dato, no escribir SQL.
