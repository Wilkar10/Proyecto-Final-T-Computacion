# API Product Canvas · LOGISTPULSE
Mismo formato del canvas de Smart Inventory. Los valores marcados *(propuesta)* son supuestos del laboratorio, no compromisos medidos.

## Canvas 1 · fleet-orders (Pedidos y Flota) · API v1 · Eventos v1
| Campo | Contenido |
|---|---|
| Propuesta de valor | Única fuente de verdad de pedidos, flota y viajes; despacha un viaje multi-parada **todo o nada** y sin duplicar. |
| Funciones clave | Consultar pedidos/robots; crear viaje (atómico, idempotente); publicar `order.dispatched` y `trip.created`. |
| Protocolo síncrono | HTTP/JSON, REST. **Público (vía gateway):** `http://localhost:8000/api/v1/**`. Interno: `http://localhost:8080/api/**` (el gateway reescribe `/api/v1` → `/api`). |
| Agregados y entidades | Order · Robot · Trip (agregado) · OutboxEvent (técnico). |
| Parámetros | `status, page, size` en GET; `Idempotency-Key` (header, **requerido** en POST); `X-Api-Key` (**requerido** vía gateway y en modo docker); `X-Request-Id` (opcional: se conserva si es seguro, si no se genera). |
| Seguridad y límites | API key por cliente con permisos `read` (GET/HEAD/OPTIONS) y `write` (POST/PUT/PATCH/DELETE). Límite de tasa por cliente: ráfaga 20, recarga 10/s *(propuesta)*; al excederlo **429** con `Retry-After`. Lo aplican el gateway (Kong) y, como defensa en profundidad, el servicio. |
| Peticiones | `POST /api/trips {robot, orders[1..12]}` |
| Respuestas | 200 listado · 201 Trip · 200 replay · 400 cuerpo inválido · **401 sin clave o clave falsa · 403 clave sin permiso `write` · 429 límite de tasa (Retry-After)** · 404 robot/pedido · 409 robot no libre, batería < reserva o pedido ya despachado · 422 destino inalcanzable. |
| Protocolo asíncrono | AMQP 0-9-1 (RabbitMQ), exchange `logistpulse.events` (topic), Outbox, al-menos-una-vez. |
| Eventos que envía | `order.dispatched`, `trip.created` (consumen analytics-lakehouse y dispatch-decision). |
| Eventos que recibe | Ninguno. |
| Calidad | Nunca pedido en dos viajes; batería nunca por debajo de la reserva (20 %); si cae RabbitMQ, los viajes siguen y los eventos esperan en el outbox. Latencias: *(propuesta)* p95 consulta < 200 ms, comando < 400 ms. |
| Abiertas | No hay cancelación de viajes; el lab aún no publica el envelope (ver `ARQUITECTURA_MICROSERVICIOS_API_FIRST.md` §5). |

## Canvas 2 · dispatch-decision (Decisión de despacho) · API v1 · Eventos v1
| Campo | Contenido |
|---|---|
| Propuesta de valor | Propone el viaje más barato factible (exacto hasta 15 paradas) y deja a un humano la decisión de ejecutar. |
| Funciones clave | Calcular propuesta; listar/consultar; aprobar o rechazar. |
| Protocolo síncrono | HTTP/JSON. **Público (vía gateway):** `http://localhost:8000/decision/v1/**`. Interno: `http://localhost:8090/**`. |
| Agregados | Proposal (estados PENDING_APPROVAL → APPROVED/REJECTED → EXECUTED/FAILED). |
| Parámetros | `X-Approver` (header, requerido en approve/reject; identifica a la persona que decide); `X-Api-Key` (requerido vía gateway). |
| Seguridad y límites | Igual política que fleet-orders, aplicada por el gateway. **Ojo:** el servicio del agente por sí solo NO valida la clave (solo el gateway lo hace); por eso en producción se publica únicamente `:8000` (`make up-gateway-only`). `X-Approver` sigue siendo un texto sin autenticar: con el gateway sabemos QUÉ cliente llama, no QUIÉN aprueba (pendiente: identidad de persona, p. ej. OIDC). |
| Respuestas | 201 Proposal · 409 sin propuesta viable o estado inválido · 401 sin aprobador o sin clave · 403 · 429 · 404. |
| Eventos que envía | `proposal.created`, `proposal.decided` *(solo contrato)*. |
| Calidad | Autonomía nivel 1: nada se ejecuta sin humano; todo queda en auditoría; si el solver falla, hay respaldo. |
| Abiertas | Autenticación real (hoy un header de texto), publicación efectiva de eventos. |
