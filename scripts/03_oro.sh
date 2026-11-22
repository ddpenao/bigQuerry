#!/usr/bin/env bash
# PASO 2: capa oro (tablas agregadas con porcentajes) en Parquet y CSV.
source "$(dirname "$0")/comun.sh"
requiere_env
if [ -z "$(find plata/viajes -maxdepth 1 -type d -name 'fecha=*' -print -quit 2>/dev/null)" ]; then
  error "La capa plata está vacía."
  error "Reconstrúyela con: ./scripts/reconstruir.sh plata   (o todo de una vez: ./scripts/reconstruir.sh oro)"
  exit 1
fi
faltan="$(meses_incompletos_plata | tr '\n' ' ')"
[ -z "$faltan" ] || log "Aviso: plata tiene meses incompletos y oro saldrá sin ellos: $faltan (usa ./scripts/reconstruir.sh oro)"
log "PASO 2 - Capa oro"
en_contenedor tlc.oro
log "Oro en oro/parquet y oro/csv"
ls -1 oro/csv 2>/dev/null | sed 's/^/   /'
