#!/usr/bin/env bash
# Borra una capa de la PRÁCTICA (nunca la del proyecto completo ni ../TLC).
#   ./demo/borrar_capa.sh bronce | plata | oro     (pide confirmación)
#   ./demo/borrar_capa.sh plata --si                (sin preguntar)
source "$(dirname "$0")/../scripts/comun.sh"
[ -n "$(meses_demo)" ] || { error "Esta carpeta no es la de la práctica (falta DEMO_MESES en .env). No borro nada."; exit 1; }

case "${1:-}" in
  bronce) objetivo="bronce_demo" ;;
  plata)  objetivo="plata" ;;
  oro)    objetivo="oro" ;;
  *) error "Uso: $0 bronce|plata|oro [--si]"; exit 1 ;;
esac
ruta="$(realpath -m "$RAIZ/$objetivo")"
case "$ruta" in
  "$RAIZ"/*) ;;
  *) error "Ruta fuera de la carpeta de la práctica: $ruta"; exit 1 ;;
esac

if [ "${2:-}" != "--si" ]; then
  read -r -p "Se borrará $ruta. ¿Continuar? (s/N) " r
  [[ "$r" =~ ^[sS]$ ]] || { log "Cancelado"; exit 0; }
fi
rm -rf "${ruta:?}"/*
mkdir -p "$ruta"
log "Capa $1 de la práctica borrada ($ruta)"
