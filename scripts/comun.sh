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

# Ejecuta un módulo de Python dentro del contenedor (se borra al terminar)
en_contenedor() {
  requiere_env
  docker compose run --rm pipeline python -m "$@"
}

leer_env() {  # leer_env NOMBRE -> valor en .env
  grep -E "^$1=" .env | tail -1 | cut -d= -f2- || true
}
