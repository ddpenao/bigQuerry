#!/usr/bin/env bash
# Monta el proyecto principal completo en una máquina Linux nueva, con un solo comando:
#   bronce (descarga de TLC), plata y oro con Docker, y Metabase con BigQuery y el tablero.
#
#   ./scripts/montar_todo.sh
#
# Antes hay que crear las llaves de Google Cloud en credenciales/ (ver la guía):
#   credenciales/metabase-lectura.json   cuenta plotly-lectura (obligatoria, la usa Metabase)
#   credenciales/gcp-key.json            cuenta de carga (solo para 04_bigquery.sh)
#
# Se puede volver a correr cuando quieras: lo que ya está hecho se salta.
source "$(dirname "$0")/comun.sh"
INICIO=$(date +%s)

log "1/6 Revisando requisitos"
command -v docker >/dev/null || { error "Falta Docker: sudo apt install -y docker.io docker-compose-v2"; exit 1; }
docker compose version >/dev/null 2>&1 || { error "Falta docker compose: sudo apt install -y docker-compose-v2"; exit 1; }
docker info >/dev/null 2>&1 || { error "Docker no responde o tu usuario no puede usarlo: sudo usermod -aG docker \$USER y reinicia"; exit 1; }
command -v python3 >/dev/null || { error "Falta python3: sudo apt install -y python3"; exit 1; }
command -v curl >/dev/null || { error "Falta curl: sudo apt install -y curl"; exit 1; }
LLAVE_LECTURA="$(leer_env MB_LLAVE_LECTURA)"; LLAVE_LECTURA="${LLAVE_LECTURA:-credenciales/metabase-lectura.json}"
if [ ! -s "$LLAVE_LECTURA" ]; then
  error "Falta la llave de Metabase en $LLAVE_LECTURA (cuenta plotly-lectura). Créala primero; ver la guía, paso 3."
  exit 1
fi
[ -s credenciales/gcp-key.json ] || log "   Aviso: no hay credenciales/gcp-key.json; no hace falta salvo para 04_bigquery.sh"

log "2/6 Capa bronce (32 Parquet de TLC)"
"$RAIZ/scripts/descargar_bronce.sh"

log "3/6 Entorno e imagen Docker"
ENV_NUEVO=0; [ -f .env ] || ENV_NUEVO=1
"$RAIZ/scripts/00_preparar.sh"
if [ $ENV_NUEVO -eq 1 ]; then
  RAM_GB=$(free -g | awk '/^Mem:/{print $2}')
  if [ "$RAM_GB" -ge 7 ]; then MEM=4g; else MEM=3g; fi
  sed -i "s/^SPARK_MEMORIA=.*/SPARK_MEMORIA=$MEM/" .env
  log "   SPARK_MEMORIA=$MEM (la máquina tiene ${RAM_GB} GB de RAM)"
fi

log "4/6 Plata y oro"
if [ -z "$(meses_incompletos_plata)" ] && [ "$(ls oro/parquet 2>/dev/null | wc -l)" -ge 12 ]; then
  log "   plata y oro ya están completos"
else
  "$RAIZ/scripts/reconstruir.sh" oro
fi

log "5/6 Metabase"
CONTENEDOR="$(leer_env MB_CONTENEDOR)"; CONTENEDOR="${CONTENEDOR:-metabase}"
PUERTO="$(leer_env MB_PUERTO)"; PUERTO="${PUERTO:-3001}"
DATOS_MB="$(leer_env MB_DATOS)"; DATOS_MB="${DATOS_MB:-$HOME/metabase-data}"
mkdir -p "$DATOS_MB"
if docker container inspect "$CONTENEDOR" >/dev/null 2>&1; then
  docker start "$CONTENEDOR" >/dev/null
  log "   contenedor $CONTENEDOR ya existía; arrancado"
else
  docker compose up -d metabase
fi
log "   esperando a que Metabase responda en http://localhost:$PUERTO (la primera vez tarda 1 o 2 minutos)"
for _ in $(seq 1 60); do
  curl -s "http://localhost:$PUERTO/api/health" | grep -q ok && break
  sleep 5
done
curl -s "http://localhost:$PUERTO/api/health" | grep -q ok || { error "Metabase no respondió. Revisa: docker logs $CONTENEDOR"; exit 1; }

log "6/6 Conexión a BigQuery y tablero"
python3 "$RAIZ/metabase/configurar.py" --url "http://localhost:$PUERTO"

"$RAIZ/scripts/estado.sh"
log "Todo listo en $(( ($(date +%s) - INICIO) / 60 )) min. Abre http://localhost:$PUERTO"
