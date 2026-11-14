#!/usr/bin/env bash
# PASO 1: capa plata. Sin argumentos procesa todos los meses.
#   ./scripts/02_plata.sh                         todos los meses
#   ./scripts/02_plata.sh --meses 2026-08         un mes
#   ./scripts/02_plata.sh --meses ultimos:2       los dos más recientes
source "$(dirname "$0")/comun.sh"
log "PASO 1 - Capa plata $*"
en_contenedor tlc.plata "$@"
log "Plata en plata/viajes (particionada por fecha). Descartes: reportes/descartes_resumen.md"
