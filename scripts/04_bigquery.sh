#!/usr/bin/env bash
# PASO 3: carga a BigQuery con load jobs (gratis).
#   ./scripts/04_bigquery.sh --solo-estimar   calcula tamaños, no sube nada
#   ./scripts/04_bigquery.sh --solo-oro       sube solo las tablas oro
#   ./scripts/04_bigquery.sh                  sube oro + los meses de plata de BQ_PLATA_MESES
source "$(dirname "$0")/comun.sh"
requiere_env
if [[ " $* " != *" --solo-estimar "* ]]; then
  [ -n "$(leer_env GCP_PROYECTO)" ] || { error "Define GCP_PROYECTO en .env"; exit 1; }
  [ -f credenciales/gcp-key.json ] || { error "Falta credenciales/gcp-key.json (ver README, sección BigQuery)"; exit 1; }
fi
log "PASO 3 - Carga a BigQuery $*"
set +e
en_contenedor tlc.bigquery_carga "$@"
codigo=$?
set -e
if [ $codigo -eq 3 ]; then
  error "Detenido a propósito: hay que decidir qué meses de plata subir (BQ_PLATA_MESES en .env)."
elif [ $codigo -ne 0 ]; then
  error "La carga terminó con error ($codigo). Revisa logs/03_bigquery_*.log"
fi
exit $codigo
