#!/usr/bin/env bash
# Funciones compartidas por todos los scripts. No se ejecuta solo.
set -euo pipefail
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$RAIZ"

log()   { echo -e "\033[1;34m[$(date '+%H:%M:%S')]\033[0m $*"; }
error() { echo -e "\033[1;31m[ERROR]\033[0m $*" >&2; }

requiere_env() {
  if [ ! -f .env ]; then
    error "Falta el archivo .env. Ejecuta primero: ./scripts/00_preparar.sh"
    exit 1
  fi
}

leer_env() {  # leer_env NOMBRE -> valor en .env (vacío si no está)
  [ -f .env ] || return 0
  grep -E "^$1=" .env | tail -1 | cut -d= -f2- | tr -d '\r' || true
}

# ---------- Rutas y estado de las capas ----------
ruta_bronce() { local b; b="$(leer_env RUTA_BRONCE_HOST)"; echo "${b:-../TLC}"; }
bronce_desde() { local v; v="$(leer_env BRONCE_DESDE)"; echo "${v:-2024-01}"; }
bronce_hasta() { local v; v="$(leer_env BRONCE_HASTA)"; echo "${v:-2026-08}"; }

meses_esperados() {  # todos los meses AAAA-MM entre BRONCE_DESDE y BRONCE_HASTA
  local m h; m="$(bronce_desde)"; h="$(bronce_hasta)"
  while [[ "$m" < "$h" || "$m" == "$h" ]]; do
    echo "$m"; m="$(date -d "$m-01 +1 month" +%Y-%m)"
  done
}

meses_faltantes_bronce() {  # meses sin su Parquet en bronce
  local m
  for m in $(meses_esperados); do
    [ -n "$(find "$(ruta_bronce)" -name "yellow_tripdata_$m.parquet" -size +0 -print -quit 2>/dev/null)" ] || echo "$m"
  done
}

meses_incompletos_plata() {  # meses de plata que no tienen todos sus días
  local m dias esperados
  for m in $(meses_esperados); do
    dias=$(find plata/viajes -maxdepth 1 -type d -name "fecha=$m-*" 2>/dev/null | wc -l || true)
    esperados=$(date -d "$m-01 +1 month -1 day" +%d | sed 's/^0//')
    [ "$dias" -ge "$esperados" ] || echo "$m"
  done
}

tablas_oro_faltantes() {
  local t
  for t in oro_kpi_mensual oro_kpi_anual oro_categoria_mensual oro_categoria_anual; do
    ls oro/parquet/$t/part-*.parquet >/dev/null 2>&1 || echo "$t"
  done
}

# Crea las carpetas con el usuario actual ANTES de abrir el contenedor.
# Si no existen, Docker las crea como root y después el pipeline no puede escribir en ellas.
asegurar_carpetas() {
  mkdir -p plata oro logs reportes datos_referencia credenciales "$(ruta_bronce)"
}

# Ejecuta un módulo de Python dentro del contenedor (se borra al terminar)
en_contenedor() {
  requiere_env
  asegurar_carpetas
  docker compose run --rm pipeline python -m "$@"
}
