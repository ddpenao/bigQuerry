#!/usr/bin/env bash
# Muestra qué tiene cada capa y qué le falta. No modifica nada.
#   ./scripts/estado.sh
source "$(dirname "$0")/comun.sh"

total_meses=$(meses_esperados | wc -l)
faltan_b=$(meses_faltantes_bronce | tr '\n' ' ')
faltan_p=$(meses_incompletos_plata | tr '\n' ' ')
faltan_o=$(tablas_oro_faltantes | tr '\n' ' ')
n_b=$(( total_meses - $(meses_faltantes_bronce | wc -l) ))
n_p=$(( total_meses - $(meses_incompletos_plata | wc -l) ))
dias=$(find plata/viajes -maxdepth 1 -type d -name 'fecha=*' 2>/dev/null | wc -l || true)
tam() { [ -e "$1" ] && du -sh "$1" 2>/dev/null | cut -f1 || echo "0 B"; }

linea() {  # linea CAPA DETALLE FALTANTES
  if [ -z "$3" ]; then
    printf "  %-7s \033[1;32mCOMPLETA\033[0m  %s\n" "$1" "$2"
  else
    printf "  %-7s \033[1;31mINCOMPLETA\033[0m %s\n          falta: %s\n" "$1" "$2" "$3"
  fi
}

log "Estado de las capas (meses: $(meses_esperados | paste -sd, -))"
linea "Bronce" "$n_b de $total_meses archivos en $(ruta_bronce) ($(tam "$(ruta_bronce)"))" "$faltan_b"
linea "Plata"  "$n_p de $total_meses meses completos, $dias días ($(tam plata/viajes))" "$faltan_p"
linea "Oro"    "$(( $(echo $TABLAS_ORO | wc -w) - $(tablas_oro_faltantes | wc -l) )) de $(echo $TABLAS_ORO | wc -w) tablas en oro/parquet" "$faltan_o"
if [ -n "$faltan_b$faltan_p$faltan_o" ]; then
  log "Para rehacer lo que falta: ./scripts/reconstruir.sh todo"
fi
