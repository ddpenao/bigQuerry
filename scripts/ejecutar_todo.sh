#!/usr/bin/env bash
# Ejecuta el pipeline completo en orden.
#   ./scripts/ejecutar_todo.sh                   bronce -> plata -> oro (todos los meses)
#   ./scripts/ejecutar_todo.sh --demo            reprocesa solo el último mes (rápido, para presentar)
#   ./scripts/ejecutar_todo.sh --con-bigquery    además carga a BigQuery al final
source "$(dirname "$0")/comun.sh"
DEMO=0; BQ=0
for a in "$@"; do
  case "$a" in
    --demo) DEMO=1 ;;
    --con-bigquery) BQ=1 ;;
    *) error "Opción desconocida: $a"; exit 1 ;;
  esac
done
INICIO=$(date +%s)
"$RAIZ/scripts/01_reconocimiento.sh"
if [ $DEMO -eq 1 ]; then
  "$RAIZ/scripts/02_plata.sh" --meses ultimos:1
else
  "$RAIZ/scripts/02_plata.sh"
fi
"$RAIZ/scripts/03_oro.sh"
[ $BQ -eq 1 ] && "$RAIZ/scripts/04_bigquery.sh"
log "Pipeline terminado en $(( ($(date +%s) - INICIO) / 60 )) min"
