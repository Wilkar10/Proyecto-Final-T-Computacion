# Proyecto final · Diseño de Sistemas — «Seis patrones, cada uno con una razón»

> **Empiecen por `HOJA_DE_ACCIONES.md`** (1 página): pasos exactos, qué deben ver y las decisiones a defender.

**Qué es:** la pieza de Diseño de Sistemas del proyecto final LOGISTPULSE: un desarrollo (`lp_patterns`, **14 pruebas verdes**) que compone **seis patrones** (los cuatro pedidos —Command, Strategy, Observer, Template Method— más Decorator y Adapter) alrededor del agente **sin modificar `base/agent`**. Su trabajo es **entender por qué cada patrón está donde está**, exponerlo y decidir con criterio cuándo un patrón ayuda y cuándo estorba. Es independiente de los otros deberes.

## Su aporte a los KPI de negocio
**KPI que mueve:** **SLA por segmento** y **agilidad para cambiar la política** sin riesgo. Strategy permite comparar criterios (prioridad, cercanía, plazo) sobre los mismos datos; Observer y Decorator dan trazabilidad y métricas.
**Evidencia del lab de decisión:** con holgura de flota las políticas casi empatan; con flota reducida el SLA corporativo va de 93,7 % a 97,2 % según el criterio. Su análisis debe responder: ¿quién decide la política de despacho, con qué KPI se compara y cada cuánto se revisa, y cuánto cuesta cambiarla?

## Los seis patrones (4 pedidos + 2 elegidos: Decorator y Adapter)
| Patrón | Dónde | Problema que resuelve | Alternativa más simple (y su costo) |
|---|---|---|---|
| **Strategy** | `strategy.py` · `PolicyPlanner` + `PriorityFirst/ClosestFirst/ValueDensity` | La regla de «qué pedidos intentamos primero» es de negocio y cambia | `if/elif` en el planificador: cada política nueva toca código probado |
| **Command** | `command.py` · `PlanCommand/ApproveCommand/RejectCommand` + `CommandBus` | HTTP, CLI y chat ejecutan las mismas acciones con historial y (a veces) deshacer | Llamar `agent.decide` desde cada canal: sin trazabilidad uniforme |
| **Observer** | `observer.py` · `EventBus`, `ObservableAudit`, `MetricsObserver`, `ApproverNotifier` | Métricas y notificaciones sin que el agente las conozca | Que el agente llame a métricas/notificador: acoplamiento y fallos en cascada |
| **Template Method** | `template.py` · `ProposalRenderer` → `MarkdownRenderer`, `PlainRenderer` | Mismo esqueleto de mensaje, distinto canal | Copiar y pegar por canal: el orden del mensaje diverge |
| **Decorator** | `decorator.py` · `RetryingActuator`, `AuditedActuator` | Reintentos y auditoría apilables sobre cualquier actuador | Meterlo en cada actuador: duplicación y mezcla de responsabilidades |
| **Adapter** | `adapter.py` · `LabOrderAdapter`, `ToolCallsLLMAdapter` | Interfaces ajenas (DTO del lab, API de otro proveedor de IA) al contrato del agente | Que el planificador conozca cada proveedor: lock-in |

La **composición** está en `compose.py` (único lugar donde se ensambla todo; sobre la arquitectura de puertos y adaptadores del agente base).

Decisiones finas que deben saber defender: el **orden** de los decoradores (`Audited` por fuera de `Retrying` oculta los reintentos transitorios), por qué los **observadores no pueden tumbar** al agente, por qué `Approve/Reject` **no son reversibles** pero `Plan` sí lo es mientras esté pendiente.

## Microservicios y APIs dirigidas por contrato (la mirada de arquitectura)
Esta materia es la dueña de **dónde se parte el sistema y por qué**. Lean `../../docs/ARQUITECTURA_MICROSERVICIOS_API_FIRST.md` (descomposición por contextos acotados, **ADR-001**: monolito modular para Pedidos y Flota; servicios separados donde hay razón) y los contratos en `../../contracts/`.
- **Observer ↔ eventos de dominio.** `EventBus` es interno al proceso; `proposal.created` y `proposal.decided` (AsyncAPI) son su versión entre servicios. Tarea: escribir un observador que publique esos eventos con el *envelope* del contrato (sin tocar el agente) y validar su salida contra `contracts/schemas/`. Discutan qué se pierde al pasar de memoria a red (orden, duplicados, falla del broker).
- **Adapter ↔ capa anticorrupción.** `LabOrderAdapter` protege al agente del modelo de `fleet-orders`; si el contrato cambia, solo cambia el adaptador.
- **Command ↔ API.** `approve/reject` son comandos con `X-Approver`; el contrato fija sus respuestas 401/404/409.
- **Límites.** Dibujen el diagrama C4 (contexto y contenedores) de LOGISTPULSE e indiquen **qué es hoy un servicio independiente y qué no**; propongan una saga para separar Flota de Pedidos y digan por qué ADR-001 aún no la justifica.

## Ponerlo a funcionar
```bash
make test-diseno                                    # 14 pruebas
cd deberes/diseno-sistemas && python - <<'PY'
import sys; sys.path[:0]=["../../base/agent","."]
from lp_patterns import compose
from lp_patterns.command import PlanCommand, ApproveCommand
w = compose.build(strategy="closest_first")
p, _ = w.commands.run(PlanCommand(w.agent)); print(w.notifier.outbox[0])
print(w.commands.run(ApproveCommand(w.agent, p.proposal_id, "ana")).status, dict(w.metrics.counts))
PY
```

## Qué deben exponer (12 min) — guion sugerido
1. **Mapa** (2 min): diagrama de cómo los seis patrones rodean al agente (dibujen cajas y flechas; nada dentro de `base/agent` cambia).
2. **Tres patrones a fondo** (4 min): problema → alternativa descartada → consecuencias (positivas y negativas). El jurado elige un cuarto.
3. **Demo en vivo** (3 min): cambien `LP_STRATEGY` o agreguen un `Renderer` nuevo (p. ej. «Slack») **sin tocar el agente**; muestren que un observador defectuoso no rompe nada.
4. **ADR y análisis** (3 min): una decisión de arquitectura documentada con alternativas.

## Preguntas que debe poder responder el equipo
- ¿Por qué `fleet-orders` sigue como monolito modular y qué evidencia cambiaría el ADR-001?
- ¿Qué garantías pierde un Observer interno cuando se convierte en evento por RabbitMQ (orden, duplicados, atomicidad)?
- ¿Cuál de los seis patrones eliminarían si el equipo fuera de 2 personas? ¿Por qué?
- Strategy vs `if/elif`: ¿a partir de cuántas políticas se justifica?
- Observer: ¿qué ocurre con el orden de notificación y con observadores lentos? ¿Cuándo pasarían a una cola de mensajes?
- Decorator: demuestren qué cambia en la auditoría si invierten el orden de las capas.
- Command: ¿por qué no se puede «deshacer» una aprobación humana ya ejecutada? ¿Cómo se corrige un error (compensación)?
- Adapter: ¿qué cambia si el nuevo proveedor de IA no soporta herramientas (tool calls)?

## Análisis estratégico — escenarios (elijan UNO)
- **A. Nuevo canal.** Gerencia pide aprobar por Slack/WhatsApp. ¿Qué piezas se tocan, cuáles no, cuánto cuesta y qué riesgo de seguridad aparece (identidad del aprobador)?
- **B. Cambio de proveedor de IA.** El proveedor sube el precio 3 ×. ¿Qué significa el costo de salida con el Adapter? ¿Qué NO queda aislado (prompts, evaluación)?
- **C. Regulador.** Exige poder reconstruir y **revertir** decisiones del agente. ¿Qué haría Command y qué faltaría (sagas, compensaciones)?
- **D. ¿Microservicios?** La dirección quiere «pasar a microservicios». Con el ADR-001, defiendan (o refuten) separar Pedidos de Flota: costo de la saga, consistencia, equipos, disparadores medibles y qué métricas de negocio mejorarían (despachos fallidos, SLA) o empeorarían.
- **E. Cadena.** Con `make cadena`, ¿qué etapa merece un servicio propio primero y qué patrón la protegería? ¿Qué patrón eliminarían si el equipo fuera de dos personas?

## Entregables y evaluación
Formato, rúbrica (30 puntos), defensa individual y declaración de uso de IA: **`../../docs/GUIA_EXPOSICION_Y_ANALISIS.md`** (común a todas las materias). Plantilla del análisis: `informe/PLANTILLA_ANALISIS.md`.

| Criterio | Pts | Qué miraremos específicamente en esta materia |
|---|---|---|
| Dominio técnico demostrado | 7,5 | Muestran cada patrón funcionando, **cambian una pieza en vivo** (p. ej. la estrategia o el canal) sin tocar el agente y explican el diagrama |
| Calidad del análisis estratégico | 9,0 | Qué patrones valen su complejidad y cuáles serían sobre-ingeniería; ADR defendido con alternativas y costo de cambio |
| Riesgos, gobernanza y límites | 4,5 | Riesgos de acoplamiento y de excederse con patrones; fallos de observadores; qué no es reversible (Command) |
| Conexión con Deber 3 | 3,0 | Nivel de autonomía recomendado y por qué; qué cambió respecto a la revisión de literatura |
| Exposición | 3,0 | 12 min exactos, un mensaje por diapositiva |
| Preguntas | 3,0 | Evidencia o «no lo sé, lo verificaría así» |

## Independencia
Este deber usa solo `base/` y su propia carpeta. Puede entregarse aunque los otros equipos no entreguen nada. Si quieren mostrar la integración, pueden activar su adaptador con la variable `LP_ACTUATOR_PLUGIN=lp_patterns.compose:build_actuator (solo reintentos); la composición completa está en `lp_patterns.compose.build()`` (opcional, no puntúa).
