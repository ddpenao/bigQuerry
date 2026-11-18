#!/usr/bin/env bash
# PASO 1: capa plata. Sin argumentos procesa todos los meses.
#   ./scripts/02_plata.sh                         todos los meses
#   ./scripts/02_plata.sh --meses 2026-08         un mes
#   ./scripts/02_plata.sh --meses ultimos:2       los dos más recientes
source "$(dirname "$0")/comun.sh"
requiere_env
if [ -z "$(find "$(ruta_bronce)" -name 'yellow_tripdata_*.parquet' -print -quit 2>/dev/null)" ]; then
  error "La capa bronce está vacía en $(ruta_bronce)."
  error "Reconstrúyela con: ./scripts/reconstruir.sh bronce   (o todo de una vez: ./scripts/reconstruir.sh plata)"
  exit 1
fi
faltan="$(meses_faltantes_bronce | tr '\n' ' ')"
[ -z "$faltan" ] || log "Aviso: a bronce le faltan estos meses y no quedarán en plata: $faltan"
log "PASO 1 - Capa plata $*"
en_contenedor tlc.plata "$@"
log "Plata en plata/viajes (particionada por fecha). Descartes: reportes/descartes_resumen.md"
