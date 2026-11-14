# PASO 1: capa plata. Sin argumentos procesa todos los meses.
#   scripts_windows\02_plata.bat                       todos los meses
#   scripts_windows\02_plata.bat 2026-08               un mes
#   scripts_windows\02_plata.bat 2026-07,2026-08       varios meses
#   scripts_windows\02_plata.bat ultimos:2             los dos más recientes
param([string]$Meses = "")
. "$PSScriptRoot\comun.ps1"
Log "PASO 1 - Capa plata $Meses"
if ($Meses) { $codigo = En-Contenedor tlc.plata --meses $Meses } else { $codigo = En-Contenedor tlc.plata }
Salir-SiFallo $codigo "La capa plata"
Log "Plata en plata\viajes (particionada por fecha). Descartes: reportes\descartes_resumen.md"
