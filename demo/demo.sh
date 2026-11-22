#!/usr/bin/env bash
# Corre la práctica rápida de punta a punta y muestra cuánto tardó.
#   ./demo/demo.sh             rehace solo lo que falte (bronce -> plata -> oro)
#   ./demo/demo.sh --completo  borra plata y oro de la demo y los rehace desde cero
source "$(dirname "$0")/../scripts/comun.sh"
requiere_env
[ -n "$(meses_demo)" ] || { error "Falta DEMO_MESES en .env; esta carpeta no parece la de la práctica"; exit 1; }

if [ "${1:-}" = "--completo" ]; then
  "$RAIZ/demo/borrar_capa.sh" oro --si
  "$RAIZ/demo/borrar_capa.sh" plata --si
fi
INICIO=$(date +%s)
"$RAIZ/scripts/estado.sh"
"$RAIZ/scripts/reconstruir.sh" oro
log "Práctica terminada en $(( ($(date +%s) - INICIO) / 60 )) min $(( ($(date +%s) - INICIO) % 60 )) s"
