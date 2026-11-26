# Hoja de acciones — Desarrollo de Software Moderno (1 página)

**Su rol:** responsables de liberar a producción. El pipeline, las pruebas y los escaneos ya están configurados; ustedes revisan el resultado y **deciden si se despliega**.

## Pasos (≈ 30 min)
| # | Acción | Comando / lugar | Deben ver |
|---|---|---|---|
| 1 | Verificar | `make test-dsm` | pruebas en verde |
| 2 | Levantar con la entrada única | `make up-gateway` y luego `make seguridad-smoke` | 401 sin clave, 403 sin permiso, 429 al exceder el límite |
| 3 | Ver los resultados del CI | pestaña **Actions** de GitHub: `ci-seguridad-sast`, `ci-seguridad-dast`, `ci-lab` | informes (SpotBugs, Semgrep, Trivy, ZAP) como artefactos |
| 4 | Ver el nivel de autonomía | `make autonomia` | tabla nivel 1 vs nivel 2 |
| 5 | Elegir UN escenario (A–D) y responderlo en `informe/PLANTILLA_ANALISIS.md` | — | informe |

> El docente ejecuta antes la primera corrida real (`mvn verify`, gateway, un workflow) y deja los informes disponibles. Si algo aún no se corrió, el README lo indica.

**La cadena completa** (inventario → pedidos → reposición → packing → delivery): `make cadena` muestra qué aporta cada etapa en falta de producto, error de empaque, fallidos, SLA y costo. Es simulación con supuestos; el escenario «Cadena» del README la usa.

## Decisiones que deben defender
1. **¿Se despliega o no?** Con el informe de hallazgos delante: por cada hallazgo, *arreglar*, *aceptar con razón escrita* o *excluir* (modelo: tabla de §5 de `docs/SEGURIDAD_CICD.md`).
2. **Ante la caída de Redis, ¿fail-open o fail-closed?** Hoy sigue sirviendo con límite en memoria. ¿Qué cuesta más: despachos fallidos por rechazar o riesgo por no limitar?
3. **Qué puertas conservan** si la dirección pide desplegar a diario.
4. **Nivel de autonomía 1 o 2** y qué control automatizado exigirían antes de pasar al 2.

## Entrega
Informe + 12 min de exposición + nota de auditoría de la entrega (≤ 1 página) con lo que mostraron los informes y la decisión tomada.
