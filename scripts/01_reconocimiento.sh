#!/usr/bin/env bash
# PASO 0: esquema de cada archivo + muestra aleatoria de 1.000 filas. No modifica nada.
source "$(dirname "$0")/comun.sh"
log "PASO 0 - Reconocimiento de la capa bronce"
en_contenedor tlc.reconocimiento
log "Reporte: reportes/reconocimiento.md"
