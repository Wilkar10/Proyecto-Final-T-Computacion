# Análisis estratégico · Diseño de Sistemas (patrones)
Equipo: ______  ·  Integrantes: ______  ·  Máx. 4 páginas  ·  Estructura común: `docs/GUIA_EXPOSICION_Y_ANALISIS.md`

## 1. La decisión
¿Qué patrones valen su complejidad en este sistema y cuáles serían sobre-ingeniería? ¿Qué decisión de arquitectura documentan como ADR?

## 2. Alternativas (mínimo 3, incluya «no hacer nada» y una opción de comprar/usar servicio externo)
| Alternativa | Qué ganamos | Qué perdemos / riesgo | Criterio con el que se evalúa |
|---|---|---|---|
| | | | |

## 3. Costos, beneficios y supuestos
Costo de cambio con y sin patrón (p. ej. cambiar de proveedor de IA, añadir un canal de notificación); costo cognitivo para el equipo; deuda técnica si se omite el patrón.
> Todo número lleva fuente o la etiqueta **SUPUESTO**. Indique qué dato, de cambiar, invertiría su conclusión.

## 4. Riesgos, gobernanza y límites
| Riesgo | Probabilidad / impacto | Dueño | Control existente en el sistema | Qué NO se verificó |
|---|---|---|---|---|
| Observador defectuoso que afecta al agente | | | `EventBus` aísla excepciones | |
| | | | | |

> **Si eligen el escenario D (¿microservicios?)**, incluyan en la sección 2 la alternativa «monolito modular + contratos» (ADR-001) frente a «separar Pedidos de Flota», con el costo de la saga y los disparadores medibles; en la sección 4, qué NO se verificó (sin broker real ni consumidores).

## 5. Recomendación y conexión con el Deber 3
- Nivel de autonomía recomendado para el agente (1–4) y condiciones para subir de nivel:
- Qué cambia respecto de su recomendación del Deber 3:
- Próximo paso concreto y medible (30 días):

## Evidencia de la demostración
Comando(s) ejecutados, parámetro modificado en vivo, resultado **predicho** vs **observado**:

## Declaración de uso de IA
Usamos … para … Verificamos … a mano mediante … No verificamos …
