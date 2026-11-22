#!/usr/bin/env bash
# Sube las tablas oro de la práctica a BigQuery, en el dataset tlc_taxis_demo.
# Se niega a subir si el .env apunta al dataset del proyecto completo (tlc_taxis).
# Las cargas son load jobs (gratis) y las tablas pesan pocos MB.
source "$(dirname "$0")/../scripts/comun.sh"
requiere_env
DATASET="$(leer_env BQ_DATASET)"
if [ -z "$DATASET" ] || [ "$DATASET" = "tlc_taxis" ]; then
  error "BQ_DATASET en .env es '$DATASET'. La práctica solo sube a tlc_taxis_demo; no subo nada."
  exit 1
fi
[ -n "$(tablas_oro_faltantes)" ] && { error "Faltan tablas oro: $(tablas_oro_faltantes | tr '\n' ' '). Corre ./demo/demo.sh"; exit 1; }

# La llave se copia del proyecto completo solo a esta carpeta local (credenciales/ no va a git)
if [ ! -f credenciales/gcp-key.json ] && [ -f ../TLC_pipeline/credenciales/gcp-key.json ]; then
  cp ../TLC_pipeline/credenciales/gcp-key.json credenciales/gcp-key.json
  chmod 600 credenciales/gcp-key.json
fi
log "Subiendo oro de la práctica a $(leer_env GCP_PROYECTO).$DATASET"
"$RAIZ/scripts/04_bigquery.sh" --solo-oro
