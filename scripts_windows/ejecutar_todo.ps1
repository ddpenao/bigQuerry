# Ejecuta el pipeline completo en orden.
#   scripts_windows\ejecutar_todo.bat                  bronce -> plata -> oro (todos los meses)
#   scripts_windows\ejecutar_todo.bat -Demo            reprocesa solo el último mes (rápido, para presentar)
#   scripts_windows\ejecutar_todo.bat -ConBigquery     además carga a BigQuery al final
param([switch]$Demo, [switch]$ConBigquery)
. "$PSScriptRoot\comun.ps1"
$inicio = Get-Date
& "$PSScriptRoot\01_reconocimiento.ps1"; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($Demo) { & "$PSScriptRoot\02_plata.ps1" -Meses "ultimos:1" } else { & "$PSScriptRoot\02_plata.ps1" }
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& "$PSScriptRoot\03_oro.ps1"; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
if ($ConBigquery) { & "$PSScriptRoot\04_bigquery.ps1"; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } }
Log ("Pipeline terminado en {0:N0} min" -f ((Get-Date) - $inicio).TotalMinutes)
