#!/usr/bin/env bash
# Deja todo listo: .env, carpetas, tabla de zonas, imagen Docker y repositorio git.
# Se ejecuta una vez (o cuando cambie el Dockerfile).
source "$(dirname "$0")/comun.sh"

log "1/6 Verificando Docker y git"
command -v docker >/dev/null || { error "Docker no está instalado"; exit 1; }
docker compose version >/dev/null || { error "Falta 'docker compose'"; exit 1; }
docker info >/dev/null 2>&1 || { error "El servicio de Docker no responde (prueba: sudo systemctl start docker)"; exit 1; }
command -v git >/dev/null || { error "git no está instalado"; exit 1; }

log "2/6 Archivo .env"
if [ ! -f .env ]; then
  cp plantilla_env.txt .env
  log "   .env creado desde plantilla_env.txt"
fi
sed -i "s/^UID=.*/UID=$(id -u)/; s/^GID=.*/GID=$(id -g)/" .env

log "3/6 Carpetas de trabajo"
mkdir -p plata oro logs reportes datos_referencia credenciales

log "4/6 Capa bronce (solo lectura)"
BRONCE="$(leer_env RUTA_BRONCE_HOST)"; BRONCE="${BRONCE:-../TLC}"
N=$(find "$BRONCE" -name 'yellow_tripdata_*.parquet' 2>/dev/null | wc -l)
if [ "$N" -eq 0 ]; then
  error "No encontré archivos yellow_tripdata_*.parquet en $BRONCE (revisa RUTA_BRONCE_HOST en .env)"
  exit 1
fi
log "   $N archivos Parquet en $BRONCE"

log "5/6 Tabla de zonas de TLC (para la dimensión distrito)"
ZONAS=datos_referencia/taxi_zone_lookup.csv
if [ -s "$ZONAS" ]; then
  log "   ya existe $ZONAS"
elif curl -fsSL https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv -o "$ZONAS"; then
  log "   descargada: $(($(wc -l < "$ZONAS") - 1)) zonas"
else
  rm -f "$ZONAS"
  error "No se pudo descargar. El pipeline sigue funcionando, pero sin distrito_origen."
fi

log "6/6 Imagen Docker (la primera vez tarda varios minutos)"
docker compose build

if [ ! -d .git ]; then
  git init -b main >/dev/null
  log "   repositorio git inicializado (rama main)"
fi
log "Listo. Siguiente paso: ./scripts/01_reconocimiento.sh  o  ./scripts/ejecutar_todo.sh"
