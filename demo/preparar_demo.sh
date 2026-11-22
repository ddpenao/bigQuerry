#!/usr/bin/env bash
# Deja lista la práctica rápida (2 meses por año). Se ejecuta una vez, dentro de la carpeta TLC_demo.
# No toca el proyecto completo (../TLC_pipeline), ni la bronce original (../TLC), ni BigQuery, ni Metabase.
source "$(dirname "$0")/../scripts/comun.sh"

COMPLETO=../TLC_pipeline

log "1/4 Archivo .env de la práctica"
if [ ! -f .env ]; then
  cp plantilla_env.txt .env
  sed -i "s/^UID=.*/UID=$(id -u)/; s/^GID=.*/GID=$(id -g)/" .env
  # Solo se copia el ID del proyecto, por si algún día quieres subir la demo a tlc_taxis_demo
  if [ -f "$COMPLETO/.env" ]; then
    p="$(grep -E '^GCP_PROYECTO=' "$COMPLETO/.env" | tail -1 | cut -d= -f2-)"
    [ -n "$p" ] && sed -i "s/^GCP_PROYECTO=.*/GCP_PROYECTO=$p/" .env
  fi
  log "   .env creado (meses: $(leer_env DEMO_MESES))"
else
  log "   ya existe .env"
fi

log "2/4 Carpetas y tabla de zonas"
mkdir -p plata oro logs reportes datos_referencia credenciales bronce_demo
if [ ! -s datos_referencia/taxi_zone_lookup.csv ] && [ -s "$COMPLETO/datos_referencia/taxi_zone_lookup.csv" ]; then
  cp "$COMPLETO/datos_referencia/taxi_zone_lookup.csv" datos_referencia/
fi
[ -s datos_referencia/taxi_zone_lookup.csv ] && log "   tabla de zonas lista" || error "   falta datos_referencia/taxi_zone_lookup.csv"

log "3/4 Imagen Docker"
if docker image inspect tlc-pipeline:1.0 >/dev/null 2>&1; then
  log "   se reutiliza tlc-pipeline:1.0 (la misma del proyecto completo)"
else
  docker compose build
fi

log "4/4 Bronce de la práctica (copia desde ../TLC, sin internet)"
"$RAIZ/scripts/reconstruir.sh" bronce
log "Listo. Para correr la práctica: ./demo/demo.sh"
