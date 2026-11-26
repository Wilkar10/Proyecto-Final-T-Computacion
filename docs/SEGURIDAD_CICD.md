# Seguridad en CI/CD · SAST, DAST y la capa de API

**Respuesta corta:** las pruebas de SAST y DAST se **definen en este repositorio** (carpeta `.github/workflows/` y archivos de configuración) y se **ejecutan en GitHub Actions**. No hay que copiarlas a otro lugar ni correrlas «aquí» a mano: el mismo recorrido se puede repetir en local con `make`. Lo único que **no** viaja en el zip son los ajustes del repositorio en GitHub (protección de rama, escaneo de secretos, etc.): se activan una vez en *Settings*.

## 1. Qué va dónde

| Pieza | Dónde vive | Ejecuta |
|---|---|---|
| Pipelines (`ci-seguridad-sast.yml`, `ci-seguridad-dast.yml`, `codeql.yml`, `ci-lab.yml`) | repositorio, `.github/workflows/` | GitHub Actions |
| Configuración de las herramientas (`.bandit`, `base/lab/spotbugs-exclude.xml`, `base/gateway/trivy*.yaml`, `base/gateway/zap-rules.conf`) | repositorio | las herramientas, en CI y en local |
| Humo de seguridad (`contracts/tools/security_smoke.py`) y lanzador de ZAP (`base/gateway/run_zap.sh`) | repositorio | CI y `make` |
| Actualización automática de dependencias (`.github/dependabot.yml`) y dueños de revisión (`CODEOWNERS`) | repositorio | GitHub |
| Resultados SARIF (Code scanning), alertas de Dependabot, escaneo de secretos, **reglas de protección de rama** | **ajustes de GitHub** (no están en el zip) | GitHub |

## 2. SAST, SCA, secretos y DAST: qué hace cada uno aquí

| Tipo | Herramienta | Job / flujo | ¿Bloquea? | Local |
|---|---|---|---|---|
| SAST Java | CodeQL (ya existía) · SpotBugs + Find Security Bugs | `codeql.yml` · `spotbugs` | CodeQL: informa · SpotBugs: sí (media o más) | `make sast-java` |
| SAST Python | CodeQL · Bandit | `codeql.yml` · `bandit` | Bandit: sí (media o más) | `make sast` |
| SAST multilenguaje | Semgrep (OWASP Top 10, Java, Python, Dockerfile, secretos) | `semgrep` | sí | `make sast-docker` |
| SCA (dependencias) | pip-audit · Trivy `fs` · Dependency Review (en PR) · Dependabot | `pip-audit`, `trivy-repo`, `revision-de-dependencias` | sí: CRITICAL/HIGH con corrección disponible | `make sast` |
| SCA de imágenes | Trivy | `ci-lab.yml` (lab) · `imagen-agente` (agente) | sí | — |
| Secretos | Trivy `secret` (+ Semgrep `p/secrets`) | `trivy-repo` | sí, salvo las claves `lab-dev-*` permitidas por escrito en `base/gateway/trivy-secret.yaml` | `make sast-docker` |
| Configuración insegura (IaC) | Trivy `config` sobre Dockerfile y compose | `trivy-repo` | no (informativo) | `docker run aquasec/trivy config .` |
| **DAST fase 1** (comportamiento) | `security_smoke.py` | `ci-seguridad-dast.yml` | sí | `make seguridad-smoke` |
| **DAST fase 2** (ataque) | OWASP ZAP `zap-api-scan` con el **contrato OpenAPI** como mapa | `ci-seguridad-dast.yml` | sí, solo reglas `FAIL` (inyección, XSS, path traversal…) | `make dast` |

**Por qué el DAST necesita el stack vivo:** SAST lee código; DAST *ataca la aplicación en ejecución*. Por eso el pipeline levanta `docker compose` dentro del runner, espera a que respondan el gateway y el agente, ejecuta las dos fases y apaga todo. Es más lento y caro que SAST: corre semanal, a mano y en los PR que tocan el lab, el gateway o los contratos.

**Idea de diseño que se explica en clase:** el contrato OpenAPI no solo sirve para generar clientes y detectar cambios incompatibles; también le dice a ZAP qué rutas, parámetros y métodos existen. *Contract-first* mejora la cobertura del DAST sin escribir un solo caso a mano.

**Por qué el DAST se divide en dos fases.** El límite de tasa es una defensa: si ZAP lanza cientos de peticiones con el límite de producción, casi todo sería `429` y el escaneo no probaría nada. La fase 1 prueba el límite tal como está (ráfaga 20, 10/s); luego se reinicia solo el servicio con límites enormes (`LAB_RATE_BURST`, `LAB_RATE_REFILL`) para que ZAP llegue a la lógica de la API. Es el mismo código con otros números.

## 3. Cómo se encadena en el flujo de trabajo

1. **Antes de subir (local):** `make sast` y `make test` — segundos.
2. **En el pull request:** SAST, SCA, secretos, pruebas de contrato y revisión de dependencias — minutos. Bloquean el *merge* si están marcados como obligatorios (ver §4).
3. **En `main`, semanal y a demanda:** el SAST se repite (aparecen CVE nuevas aunque el código no cambie) y corre el DAST completo.
4. **Al crear una etiqueta `vX.Y.Z`** (`cd.yml`): se construyen y publican las imágenes. Siguiente paso recomendado: que `cd.yml` dependa de los jobs de seguridad.

## 4. Ajustes de GitHub que hay que activar (una vez)

No se pueden poner en un archivo del repositorio; se hacen en *Settings* del repositorio u organización:

1. **Code security → Dependency graph y Dependabot alerts** (la revisión de dependencias en PR los necesita).
2. **Code scanning** (aceptar los SARIF de Semgrep y Trivy). En repositorios *privados* requiere GitHub Advanced Security; sin ella, las herramientas igual corren y bloquean, pero los resultados se leen en el log y en los artefactos.
3. **Secret scanning + Push protection.**
4. **Reglas de protección de rama (`main`)**: exigir pull request, exigir revisión de `CODEOWNERS` y marcar como **comprobaciones obligatorias** los jobs: `SAST Python (Bandit)`, `SAST Java (SpotBugs + Find Security Bugs)`, `SAST multilenguaje (Semgrep)`, `SCA Python (pip-audit)`, `SCA + secretos + IaC (Trivy sobre el repositorio)`, `SCA de la imagen del agente (Trivy)`, y los de `ci-contratos`, `ci-lab`, `ci-agent`. El DAST suele quedar como obligatorio solo antes de publicar, no en cada PR.
5. **Actions → Permisos del workflow por defecto: solo lectura** (cada flujo ya declara `permissions:` mínimos).

## 5. Qué se encontró de verdad al correrlo (y cómo se resolvió)

Bandit se ejecutó sobre el código de este proyecto y encontró cosas reales. Sirven como ejemplo de **triage** (arreglar, aceptar con razón escrita, o excluir):

| Hallazgo | Dónde | Decisión |
|---|---|---|
| B310 · `urlopen` acepta esquemas como `file://` | `labclient.py`, `security_smoke.py` | **Arreglado:** se valida que el esquema sea `http`/`https` |
| B104 · el agente escuchaba en `0.0.0.0` | `lpagent/server.py` | **Arreglado:** por defecto solo `127.0.0.1`; el contenedor lo abre con `LP_BIND=0.0.0.0` |
| B608 · SQL armado con f-string | `lakehouse/.../consumer.py` | **Arreglado:** consulta parametrizada (`%s::interval`) |
| B311 · `random` no es criptográfico | simulación y semillas | **Aceptado con razón:** la simulación debe ser reproducible; no protege nada (`.bandit`) |
| B101/B107/B608 en `bases-de-datos/ci/e2e_pg.py` | script de CI contra un Postgres desechable | **Excluido con razón** (`.bandit`, `-x`) |

Además, `pip-audit` sobre las dependencias del lakehouse resolvió el árbol completo y **no encontró vulnerabilidades conocidas** (fecha de la ejecución: 2026-11-24; cambia con el tiempo, por eso corre cada semana).

Y un efecto colateral importante que el trabajo de seguridad destapó: al exigir `X-Api-Key` en modo docker, **el agente, el humo del lab, la prueba de contrato de DSM, Postman y `requests.http` dejaban de funcionar**; se les agregó la clave (`LAB_API_KEY`). Moraleja de clase: *una política de seguridad nueva rompe a los clientes existentes, y el contrato es el lugar donde se detecta*.

## 6. Qué NO cubre (límites honestos)

- No busca secretos en el **historial** de git (solo el árbol actual); para eso se añade Gitleaks en modo historial.
- No es una prueba de penetración: ZAP automatizado encuentra una parte de los problemas, no la lógica de negocio.
- La **autorización de personas** no existe: `X-Approver` es un texto. El gateway autentica *clientes*, no *personas*.
- No genera SBOM ni firma imágenes; las acciones de GitHub se fijan por etiqueta, no por SHA (Dependabot las mantiene al día; fijarlas por SHA es el siguiente endurecimiento).
- Un 429 del gateway tiene cuerpo `{"message":"RATE_LIMITED"}` y uno del servicio usa el esquema `Error`; el contrato lo documenta pero no los unifica.

## 7. Qué está verificado y qué no

**Ejecutado aquí:** Bandit y pip-audit (reales); el script Lua del límite contra un Redis 7 real; la lógica Java del token bucket y de las claves compilada y ejecutada con `javac`, y los tres filtros compilados y ejecutados contra *stubs* de JAX-RS/Spring escritos a mano; `docker compose config` de todos los perfiles; sintaxis YAML/XML de todos los archivos nuevos; las pruebas de contrato, de gateway y del script de humo (este último contra un servidor falso con fallos inyectados, para comprobar que detecta cada incumplimiento).

**No ejecutado aquí (sin red a Maven Central, a Docker Hub ni a GitHub):** la compilación con Maven y las pruebas JUnit nuevas; el arranque de Kong y del stack; **ningún workflow en GitHub Actions**; Semgrep, Trivy, SpotBugs y ZAP. Las versiones de los plugins (`spotbugs-maven-plugin 4.8.6.6`, `findsecbugs 1.13.0`, `trivy-action 0.28.0`, `kong:3.8`) y los nombres de reglas de ZAP deben confirmarse en la **primera corrida real**; es normal que ese primer intento requiera ajustes.

## 8. Tareas para los deberes

- **Desarrollo de Software Moderno:** en un PR, introducir a propósito una vulnerabilidad (p. ej. SQL por concatenación) y mostrar qué job la detecta; luego decidir si es *arreglar*, *aceptar con razón* o *excluir*, y escribirlo como en la tabla de §5. Añadir una regla `FAIL` a `zap-rules.conf` y justificarla.
- **Diseño de Sistemas:** explicar por qué el límite corre antes de la validación de la clave y qué patrón es cada filtro (cadena de responsabilidad). Proponer cómo pasar de *fail-open* a *fail-closed* y qué cambia en la métrica de despachos fallidos.
- **Bases de Datos:** mostrar que la consulta parametrizada de `consumer.py` evita el B608 y proponer el rol de solo lectura que debería usar el escaneo.
- **Teoría de la Computación:** el token bucket frente a la ventana fija: ¿cuántas peticiones pueden pasar en el peor caso en cada uno? (pista: 2×10 en el borde de ventana de Kong).
