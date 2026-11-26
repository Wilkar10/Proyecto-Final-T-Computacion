# Análisis estratégico · Desarrollo de Software Moderno
Equipo: ______  ·  Integrantes: ______  ·  Máx. 4 páginas  ·  Estructura común: `docs/GUIA_EXPOSICION_Y_ANALISIS.md`

## 1. La decisión
¿Qué prácticas de entrega (CI, puertas de calidad, escaneo, despliegue con aprobación, reversa) son el mínimo aceptable antes de dejar que un agente dispare operaciones reales?

## 2. Alternativas (mínimo 3, incluya «no hacer nada» y una opción de comprar/usar servicio externo)
| Alternativa | Qué ganamos | Qué perdemos / riesgo | Criterio con el que se evalúa |
|---|---|---|---|
| | | | |

## 3. Costos, beneficios y supuestos
Costo de la tubería (minutos de CI, mantenimiento) vs costo de un incidente; DORA (frecuencia de despliegue, tiempo de entrega, tasa de fallos, tiempo de recuperación) como indicadores; build vs buy de plataforma.
> Todo número lleva fuente o la etiqueta **SUPUESTO**. Indique qué dato, de cambiar, invertiría su conclusión.

## 4. Riesgos, gobernanza y límites
| Riesgo | Probabilidad / impacto | Dueño | Control existente en el sistema | Qué NO se verificó |
|---|---|---|---|---|
| Doble despacho por reintento | | | Idempotency-Key + UNIQUE en `trips` | El Java NO fue compilado ni ejecutado por el docente |
| Cambio incompatible de contrato rompe a un consumidor | | | `contracts/tools/validate_contracts.py` + `ci-contratos` + línea base | Spectral en CI no se ejecutó; la línea base es una copia local |
| Deriva: el lab publica eventos sin el envelope del contrato | | | Prueba de contrato (solo detecta rutas, no el formato de los eventos del lab) | El publicador Java nunca se ejecutó contra RabbitMQ |
| | | | | |

## 5. Recomendación y conexión con el Deber 3
- Nivel de autonomía recomendado para el agente (1–4) y condiciones para subir de nivel:
- Qué cambia respecto de su recomendación del Deber 3:
- Próximo paso concreto y medible (30 días):

## Evidencia de la demostración
Comando(s) ejecutados, parámetro modificado en vivo, resultado **predicho** vs **observado**:

## Declaración de uso de IA
Usamos … para … Verificamos … a mano mediante … No verificamos …
