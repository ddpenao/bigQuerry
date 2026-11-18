# PASO 1: capa plata. Sin argumentos procesa todos los meses.
#   scripts_windows\02_plata.bat                       todos los meses
#   scripts_windows\02_plata.bat 2026-08               un mes
#   scripts_windows\02_plata.bat 2026-07,2026-08       varios meses
#   scripts_windows\02_plata.bat ultimos:2             los dos más recientes
param([string]$Meses = "")
. "$PSScriptRoot\comun.ps1"
Requiere-Env
if (-not (Get-ChildItem -Path (Ruta-Bronce) -Recurse -Filter "yellow_tripdata_*.parquet" -ErrorAction SilentlyContinue | Select-Object -First 1)) {
    Fallo "La capa bronce está vacía en $(Ruta-Bronce)."
    Fallo "Reconstrúyela con: scripts_windows\reconstruir.bat bronce   (o todo de una vez: scripts_windows\reconstruir.bat plata)"
    exit 1
}
$faltan = @(Meses-FaltantesBronce)
if ($faltan.Count -gt 0) { Log "Aviso: a bronce le faltan estos meses y no quedarán en plata: $($faltan -join ' ')" }
Log "PASO 1 - Capa plata $Meses"
if ($Meses) { $codigo = En-Contenedor tlc.plata --meses $Meses } else { $codigo = En-Contenedor tlc.plata }
Salir-SiFallo $codigo "La capa plata"
Log "Plata en plata\viajes (particionada por fecha). Descartes: reportes\descartes_resumen.md"
