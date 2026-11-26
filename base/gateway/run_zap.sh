#!/usr/bin/env bash
# Ejecuta un escaneo DAST con OWASP ZAP (zap-api-scan) usando el contrato OpenAPI como mapa de ataque.
# Lo usan el pipeline (.github/workflows/ci-seguridad-dast.yml) y `make dast`, para que el resultado local sea el mismo que en GitHub.
# Uso: base/gateway/run_zap.sh <contrato.yaml> <http://host:puerto> <nombre-informe> <clave-api> [directorio-salida]
# Salida: 0 limpio · 1 hay reglas FAIL (ver base/gateway/zap-rules.conf) · 2 solo avisos (WARN) · 3 error de ejecución de ZAP
set -u
SPEC="${1:?contrato OpenAPI (nombre dentro de contracts/openapi)}"; HOST="${2:?URL base}"; NAME="${3:?nombre del informe}"; KEY="${4:?clave de API}"
OUT="${5:-zap-out}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
mkdir -p "$OUT"; chmod 777 "$OUT"
NET=(--network host)
if [ "$(uname -s)" != "Linux" ]; then      # Docker Desktop (Mac/Windows): localhost del contenedor no es el de tu máquina
  NET=(); HOST="${HOST//localhost/host.docker.internal}"
fi
docker run --rm ${NET[@]+"${NET[@]}"} \
  -v "$ROOT/contracts/openapi:/zap/spec:ro" \
  -v "$ROOT/base/gateway/zap-rules.conf:/zap/rules.conf:ro" \
  -v "$(cd "$OUT" && pwd):/zap/wrk:rw" \
  ghcr.io/zaproxy/zaproxy:stable zap-api-scan.py \
  -t "/zap/spec/$SPEC" -f openapi -O "$HOST" -c /zap/rules.conf -r "$NAME.html" -J "$NAME.json" \
  -z "-config replacer.full_list(0).description=apikey -config replacer.full_list(0).enabled=true -config replacer.full_list(0).matchtype=REQ_HEADER -config replacer.full_list(0).matchstring=X-Api-Key -config replacer.full_list(0).replacement=$KEY" >&2
rc=$?
echo "$NAME: zap-api-scan terminó con código $rc (0 limpio · 1 reglas FAIL · 2 avisos · 3 error)" >&2
exit $rc
