#!/usr/bin/env bash
# Guarda el estado del proyecto en git y lo sube al remoto si existe.
#   ./scripts/06_compartir_git.sh "mensaje del commit"
#   ./scripts/06_compartir_git.sh "mensaje" https://github.com/USUARIO/tlc-pipeline.git   (primera vez)
# Se versiona: código, Docker, scripts, README, reportes y oro/csv.
# NO se versiona: plata, oro/parquet, logs, .env ni credenciales (ver .gitignore).
source "$(dirname "$0")/comun.sh"
MENSAJE="${1:-Actualización del pipeline TLC}"
REMOTO="${2:-}"
[ -d .git ] || git init -b main >/dev/null
if [ -n "$REMOTO" ]; then
  git remote get-url origin >/dev/null 2>&1 && git remote set-url origin "$REMOTO" || git remote add origin "$REMOTO"
  log "Remoto origin → $REMOTO"
fi
git add -A
if git diff --cached --quiet; then
  log "No hay cambios para guardar"
else
  git commit -m "$MENSAJE" >/dev/null
  log "Commit creado: $(git log -1 --oneline)"
fi
if git remote get-url origin >/dev/null 2>&1; then
  git push -u origin "$(git branch --show-current)"
else
  log "Sin remoto. Para compartir: $0 \"mensaje\" https://github.com/USUARIO/REPO.git"
fi
