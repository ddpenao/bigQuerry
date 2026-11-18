#!/usr/bin/env bash
# Reconstruye una capa con un solo comando. Si le falta la capa anterior, la rehace primero.
#   ./scripts/reconstruir.sh bronce      vuelve a bajar (o copia del respaldo) los meses que falten
#   ./scripts/reconstruir.sh plata       rehace los meses de plata que falten (y bronce si hace falta)
#   ./scripts/reconstruir.sh oro         rehace oro (y plata y bronce si hace falta)
#   ./scripts/reconstruir.sh todo        revisa las tres capas y rehace lo que falte
# Opciones:
#   --completo          en plata, reprocesa los 32 meses aunque ya existan
#   --desde RUTA        copia bronce desde esa carpeta (USB, respaldo) en vez de descargarla
#                       (también se puede fijar RESPALDO_BRONCE=RUTA en .env)
source "$(dirname "$0")/comun.sh"

uso() { sed -n '2,11p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }
CAPA="${1:-}"; [ -n "$CAPA" ] || uso; shift
COMPLETO=0; DESDE="$(leer_env RESPALDO_BRONCE)"
while [ $# -gt 0 ]; do
  case "$1" in
    --completo) COMPLETO=1; shift ;;
    --desde) DESDE="${2:-}"; shift 2 ;;
    *) error "Opción desconocida: $1"; uso ;;
  esac
done
INICIO=$(date +%s)

construir_bronce() {
  local faltan; faltan=$(meses_faltantes_bronce)
  if [ -z "$faltan" ]; then log "Bronce ya está completa"; return; fi
  log "Bronce: faltan $(echo "$faltan" | wc -l) meses"
  if [ -n "$DESDE" ] && [ -d "$DESDE" ]; then
    log "   copiando desde el respaldo $DESDE"
    local m f
    for m in $faltan; do
      f=$(find "$DESDE" -name "yellow_tripdata_$m.parquet" -size +0 -print -quit 2>/dev/null)
      if [ -n "$f" ]; then
        mkdir -p "$(ruta_bronce)/${m:0:4}"
        cp "$f" "$(ruta_bronce)/${m:0:4}/" && log "   $m copiado"
      else
        error "   $m no está en el respaldo; se intentará descargar"
      fi
    done
  fi
  # Lo que siga faltando (sin respaldo o no estaba en él) se descarga de TLC
  for m in $(meses_faltantes_bronce); do
    "$RAIZ/scripts/descargar_bronce.sh" "$m" "$m"
  done
  [ -z "$(meses_faltantes_bronce)" ] || { error "Bronce sigue incompleta: $(meses_faltantes_bronce | tr '\n' ' ')"; exit 1; }
  log "Bronce completa"
}

PLATA_CAMBIO=0
construir_plata() {
  construir_bronce
  local meses
  if [ $COMPLETO -eq 1 ]; then
    meses=""
  else
    meses=$(meses_incompletos_plata | paste -sd, -)
    if [ -z "$meses" ]; then log "Plata ya está completa (usa --completo para reprocesarla entera)"; return; fi
  fi
  PLATA_CAMBIO=1
  if [ -z "$meses" ]; then
    "$RAIZ/scripts/02_plata.sh"
  else
    log "Plata: se procesan los meses que faltan: $meses"
    "$RAIZ/scripts/02_plata.sh" --meses "$meses"
  fi
}

construir_oro() {
  construir_plata
  "$RAIZ/scripts/03_oro.sh"
}

case "$CAPA" in
  bronce) construir_bronce ;;
  plata)  construir_plata ;;
  oro)    construir_oro ;;
  todo)
    construir_plata
    # Oro se rehace si le falta alguna tabla o si plata acaba de cambiar
    if [ -n "$(tablas_oro_faltantes)" ] || [ $PLATA_CAMBIO -eq 1 ]; then
      "$RAIZ/scripts/03_oro.sh"
    else
      log "Oro ya está completa"
    fi ;;
  *) uso ;;
esac
log "Reconstrucción de '$CAPA' terminada en $(( ($(date +%s) - INICIO) / 60 )) min"
"$RAIZ/scripts/estado.sh"
