# Análisis estratégico · Teoría de la Computación
Equipo: ______  ·  Integrantes: ______  ·  Máx. 4 páginas  ·  Estructura común: `docs/GUIA_EXPOSICION_Y_ANALISIS.md`

## 1. La decisión
¿Qué estrategia de solución adoptamos para el despacho multi-parada (exacto, heurístico, servicio externo) y con qué garantías hacia el negocio? Use la tabla de `docs/RESULTADOS_BENCHMARK.md` como evidencia.

## 2. Alternativas (mínimo 3, incluya «no hacer nada» y una opción de comprar/usar servicio externo)
| Alternativa | Qué ganamos | Qué perdemos / riesgo | Criterio con el que se evalúa |
|---|---|---|---|
| | | | |

## 3. Costos, beneficios y supuestos
Tiempo de cómputo vs tamaño n; costo de una propuesta subóptima (batería/tiempo de robot); costo de integrar un solver externo; qué pasa si n crece 10 ×.
> Todo número lleva fuente o la etiqueta **SUPUESTO**. Indique qué dato, de cambiar, invertiría su conclusión.

## 4. Riesgos, gobernanza y límites
| Riesgo | Probabilidad / impacto | Dueño | Control existente en el sistema | Qué NO se verificó |
|---|---|---|---|---|
| Una heurística responde «no» y se interpreta como «imposible» | | | `proven=False` + fallback + validador V | |
| | | | | |

## 5. Recomendación y conexión con el Deber 3
- Nivel de autonomía recomendado para el agente (1–4) y condiciones para subir de nivel:
- Qué cambia respecto de su recomendación del Deber 3:
- Próximo paso concreto y medible (30 días):

## Evidencia de la demostración
Comando(s) ejecutados, parámetro modificado en vivo, resultado **predicho** vs **observado**:

## Declaración de uso de IA
Usamos … para … Verificamos … a mano mediante … No verificamos …
