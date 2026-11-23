#!/usr/bin/env bash
# Copia todo lo necesario para levantar el proyecto sin internet a una memoria USB.
#
# Uso:
#   ./scripts/respaldo_memoria.sh /media/$USER/NOMBRE_MEMORIA
#   ./scripts/respaldo_memoria.sh /media/$USER/NOMBRE_MEMORIA --con-bronce   (agrega los Parquet originales)
#
# No copia credenciales (credenciales/, .env) ni la capa plata.
set -euo pipefail

DESTINO_BASE="${1:-}"
CON_BRONCE="${2:-}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
BRONCE="$HOME/Documentos/TLC"
METABASE_DATA="$HOME/metabase-data"

if [[ -z "$DESTINO_BASE" || ! -d "$DESTINO_BASE" ]]; then
  echo "Indica la carpeta de la memoria, por ejemplo: $0 /media/$USER/MIMEMORIA" >&2
  exit 1
fi

DESTINO="$DESTINO_BASE/TLC_respaldo_$(date +%F)"
mkdir -p "$DESTINO"
echo "Respaldo en: $DESTINO"

echo "1/5 Repositorio git (todas las ramas)"
git -C "$REPO" bundle create "$DESTINO/TLC_pipeline.bundle" --all

echo "2/5 Tablas oro (Parquet y CSV)"
if [[ -d "$REPO/oro" ]]; then
  cp -r "$REPO/oro" "$DESTINO/oro"
fi

echo "3/5 Metabase (preguntas y tablero)"
if [[ -d "$METABASE_DATA" ]]; then
  CORRIENDO=0
  if docker ps --format '{{.Names}}' | grep -qx metabase; then
    CORRIENDO=1
    docker stop metabase >/dev/null
  fi
  cp -r "$METABASE_DATA" "$DESTINO/metabase-data"
  [[ $CORRIENDO -eq 1 ]] && docker start metabase >/dev/null
fi
cp "$REPO/metabase/dashboard_tlc.json" "$DESTINO/" 2>/dev/null || true

echo "4/5 Imágenes de Docker (para instalar sin descargar)"
IMAGEN_METABASE="$(docker inspect --format '{{.Config.Image}}' metabase 2>/dev/null || echo metabase/metabase:latest)"
docker save "$IMAGEN_METABASE" -o "$DESTINO/imagen_metabase.tar"
for img in $(docker images --format '{{.Repository}}:{{.Tag}}' | grep -i tlc || true); do
  nombre="$(echo "$img" | tr '/:' '__')"
  docker save "$img" -o "$DESTINO/imagen_${nombre}.tar"
done

echo "5/5 Bronce"
if [[ "$CON_BRONCE" == "--con-bronce" && -d "$BRONCE" ]]; then
  cp -r "$BRONCE" "$DESTINO/bronce_TLC"
else
  echo "   omitido (agrega --con-bronce para copiarlo)"
fi

cat > "$DESTINO/LEEME.txt" <<EOF
Respaldo del proyecto TLC creado el $(date '+%F %H:%M').

Restaurar en un equipo Linux con Docker:

1. Código:
   git clone TLC_pipeline.bundle TLC_pipeline
   cd TLC_pipeline && git switch dashboard-csv

2. Imágenes de Docker (no necesitan internet):
   for f in imagen_*.tar; do docker load -i "\$f"; done

3. Metabase con el tablero ya hecho:
   cp -r metabase-data ~/metabase-data
   docker run -d -p 3001:3000 -v ~/metabase-data:/metabase-data \\
     -e MB_DB_FILE=/metabase-data/metabase.db --name metabase $IMAGEN_METABASE
   Abrir http://localhost:3001

Los gráficos consultan BigQuery, así que necesitan internet para mostrar datos.
Sin conexión quedan disponibles el código, las tablas oro (carpeta oro/) y los PDF
que se exporten desde Metabase y se guarden en esta carpeta.

La llave de Google Cloud no está en este respaldo a propósito.
EOF

du -sh "$DESTINO"
echo "Listo."
