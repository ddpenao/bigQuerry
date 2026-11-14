# Guarda el estado del proyecto en git y lo sube al remoto si existe.
#   scripts_windows\06_compartir_git.bat "mensaje del commit"
#   scripts_windows\06_compartir_git.bat "mensaje" https://github.com/USUARIO/REPO.git   (primera vez)
param([string]$Mensaje = "Actualización del pipeline TLC", [string]$Remoto = "")
. "$PSScriptRoot\comun.ps1"
if (-not (Test-Path ".git")) { & git init -b main | Out-Null }
if ($Remoto) {
    & git remote get-url origin *> $null
    if ($LASTEXITCODE -eq 0) { & git remote set-url origin $Remoto } else { & git remote add origin $Remoto }
    Log "Remoto origin -> $Remoto"
}
& git add -A
& git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
    Log "No hay cambios para guardar"
} else {
    & git commit -m $Mensaje | Out-Null
    Log "Commit creado: $(& git log -1 --oneline)"
}
& git remote get-url origin *> $null
if ($LASTEXITCODE -eq 0) {
    & git push -u origin (& git branch --show-current)
} else {
    Log 'Sin remoto. Para compartir: 06_compartir_git.bat "mensaje" https://github.com/USUARIO/REPO.git'
}
