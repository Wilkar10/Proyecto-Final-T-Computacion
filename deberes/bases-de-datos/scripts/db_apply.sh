#!/usr/bin/env bash
# Aplica en orden los scripts de sql/ (tus entregables). Deben ser idempotentes (IF NOT EXISTS / CREATE OR REPLACE).
set -euo pipefail
cd "$(dirname "$0")/.."
PSQL="${PSQL:-psql -h localhost -U lp -d logistpulse}"
shopt -s nullglob
for f in sql/[0-9]*.sql; do
  echo ">> $f"
  $PSQL -v ON_ERROR_STOP=1 -q -f "$f"
done
