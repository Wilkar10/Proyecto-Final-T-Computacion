# Hoja de acciones — Diseño de Sistemas (1 página)

**Su rol:** arquitectos que deciden dónde poner los límites. Los patrones ya están implementados y probados.

## Pasos (≈ 30 min)
| # | Acción | Comando | Deben ver |
|---|---|---|---|
| 1 | Verificar | `make test-diseno` | 14 pruebas en verde |
| 2 | Recorrer el flujo plan → aprobar | bloque de código del README de este deber | mensaje del notificador y estado del comando aprobado |
| 3 | Ver el costo de la aprobación humana | `make autonomia` | tabla nivel 1 vs nivel 2 |
| 4 | Revisar contratos y gateway | `make contratos` | contratos válidos y compatibles |
| 5 | Elegir UN escenario (A–D) y responderlo en `informe/PLANTILLA_ANALISIS.md` | — | informe |

**La cadena completa** (inventario → pedidos → reposición → packing → delivery): `make cadena` muestra qué aporta cada etapa en falta de producto, error de empaque, fallidos, SLA y costo. Es simulación con supuestos; el escenario «Cadena» del README la usa.

## Decisiones que deben defender
1. **Dónde está el límite:** qué piezas se pueden cambiar sin tocar el resto (proveedor de IA, canal de aprobación) y cuáles no.
2. **¿Separar Pedidos de Flota?** Con el ADR-001: ¿qué disparador medible los haría separarlos?
3. **Nivel de autonomía:** qué pasa en el diseño si se pasa del nivel 1 al 2 (¿quién queda como aprobador? ¿cómo se revierte un viaje sin aprobar?), con la cifra de `make autonomia`.

## Entrega
Informe + 12 min de exposición. Se evalúa el razonamiento de trade-offs, no escribir patrones.
