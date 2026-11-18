#!/usr/bin/env bash
# Descarga la capa bronce (Parquet de taxis amarillos de TLC) para quien clona el repositorio.
# Los datos no van en git porque pesan ~2 GB; son públicos y se bajan de la página de TLC.
#   ./scripts/descargar_bronce.sh                    BRONCE_DESDE a BRONCE_HASTA (por defecto 2024-01 a 2026-08, 32 archivos, ~2 GB)
#   ./scripts/descargar_bronce.sh 2026-06 2026-08    solo un rango de meses
# Los archivos que ya existen no se vuelven a descargar.
source "$(dirname "$0")/comun.sh"
command -v curl >/dev/null || { error "Falta curl (sudo apt install curl)"; exit 1; }

DESDE="${1:-$(bronce_desde)}"
HASTA="${2:-$(bronce_hasta)}"
BRONCE="$(ruta_bronce)"
URL="https://d37ci6vzurychx.cloudfront.net/trip-data"

log "Descargando $DESDE → $HASTA en $BRONCE"
mes="$DESDE"; ok=0; saltados=0; fallidos=()
while [[ "$mes" < "$HASTA" || "$mes" == "$HASTA" ]]; do
  anio="${mes:0:4}"
  destino="$BRONCE/$anio/yellow_tripdata_$mes.parquet"
  mkdir -p "$BRONCE/$anio"
  if [ -s "$destino" ]; then
    saltados=$((saltados + 1))
  elif curl -fL --retry 3 --progress-bar -o "$destino.part" "$URL/yellow_tripdata_$mes.parquet"; then
    mv "$destino.part" "$destino"; ok=$((ok + 1))
    log "   $mes ($(du -h "$destino" | cut -f1))"
  else
    rm -f "$destino.part"; fallidos+=("$mes")
    error "   $mes no se pudo descargar"
  fi
  mes="$(date -d "$mes-01 +1 month" +%Y-%m)"
done
log "Descargados: $ok | ya existían: $saltados | fallidos: ${#fallidos[@]} ${fallidos[*]:-}"
[ ${#fallidos[@]} -eq 0 ] || exit 1
