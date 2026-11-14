#!/usr/bin/env bash
# Guarda la imagen Docker en un archivo para usarla sin internet (por ejemplo en la presentación).
# En el otro equipo: docker load -i tlc-pipeline-imagen.tar.gz
source "$(dirname "$0")/comun.sh"
log "Exportando tlc-pipeline:1.0 ..."
docker save tlc-pipeline:1.0 | gzip > tlc-pipeline-imagen.tar.gz
log "Listo: tlc-pipeline-imagen.tar.gz ($(du -h tlc-pipeline-imagen.tar.gz | cut -f1))"
