# Muestra qué tiene cada capa y qué le falta. No modifica nada.
#   scripts_windows\estado.bat
. "$PSScriptRoot\comun.ps1"

function Tamano([string]$Ruta) {
    if (-not (Test-Path $Ruta)) { return "0 MB" }
    $bytes = (Get-ChildItem -Path $Ruta -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    if (-not $bytes) { $bytes = 0 }
    return ("{0:N0} MB" -f ($bytes / 1MB))
}
function Linea([string]$Capa, [string]$Detalle, [string[]]$Faltan) {
    if ($Faltan.Count -eq 0) {
        Write-Host ("  {0,-7} " -f $Capa) -NoNewline; Write-Host "COMPLETA   " -ForegroundColor Green -NoNewline; Write-Host $Detalle
    } else {
        Write-Host ("  {0,-7} " -f $Capa) -NoNewline; Write-Host "INCOMPLETA " -ForegroundColor Red -NoNewline; Write-Host $Detalle
        Write-Host "          falta: $($Faltan -join ' ')"
    }
}

$total = @(Meses-Esperados).Count
$faltanB = @(Meses-FaltantesBronce)
$faltanP = @(Meses-IncompletosPlata)
$faltanO = @(Tablas-OroFaltantes)
$dias = @(Get-ChildItem -Path "plata\viajes" -Directory -Filter "fecha=*" -ErrorAction SilentlyContinue).Count

Log "Estado de las capas (meses: $((@(Meses-Esperados)) -join ','))"
Linea "Bronce" "$($total - $faltanB.Count) de $total archivos en $(Ruta-Bronce) ($(Tamano (Ruta-Bronce)))" $faltanB
Linea "Plata"  "$($total - $faltanP.Count) de $total meses completos, $dias días ($(Tamano 'plata\viajes'))" $faltanP
Linea "Oro"    "$($TablasOro.Count - $faltanO.Count) de $($TablasOro.Count) tablas en oro\parquet" $faltanO
if (($faltanB.Count + $faltanP.Count + $faltanO.Count) -gt 0) {
    Log "Para rehacer lo que falta: scripts_windows\reconstruir.bat todo"
}
