#!/usr/bin/env bash
# Ejecuta cada checks/dq_*.sql. Una consulta que devuelve filas = control FALLIDO. Sale con 1 si alguno falla.
# Uso: scripts/db_check.sh            (usa PSQL, por defecto psql contra localhost con el rol lp)
#      PSQL="docker compose exec -T postgres psql -U lp -d logistpulse" scripts/db_check.sh
set -uo pipefail
cd "$(dirname "$0")/.."
PSQL="${PSQL:-psql -h localhost -U lp -d logistpulse}"
fail=0
for f in checks/dq_*.sql; do
  out=$($PSQL -v ON_ERROR_STOP=1 -tA -f "$f" 2>&1) || { echo "ERROR  $f"; echo "$out"; fail=1; continue; }
  if [ -n "$out" ]; then echo "FALLA  $f"; echo "$out" | head -5 | sed 's/^/         /'; fail=1; else echo "OK     $f"; fi
done
exit $fail
