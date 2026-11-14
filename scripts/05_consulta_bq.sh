#!/usr/bin/env bash
# Consulta BigQuery con dry run obligatorio y bloqueo de SELECT *.
#   ./scripts/05_consulta_bq.sh "SELECT periodo, viajes FROM \`PROYECTO.tlc_taxis.oro_kpi_mensual\` LIMIT 5"
#   ./scripts/05_consulta_bq.sh --solo-estimar "SELECT ..."
source "$(dirname "$0")/comun.sh"
[ $# -ge 1 ] || { error "Uso: $0 [--solo-estimar] \"SQL\""; exit 1; }
en_contenedor tlc.bigquery_seguro "$@"
