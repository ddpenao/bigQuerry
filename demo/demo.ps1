# Corre la práctica rápida de punta a punta y muestra cuánto tardó.
#   demo\demo.bat             rehace solo lo que falte (bronce -> plata -> oro)
#   demo\demo.bat -Completo   borra plata y oro de la práctica y los rehace desde cero
param([switch]$Completo)
. "$PSScriptRoot\..\scripts_windows\comun.ps1"
Requiere-Env
if (@(Meses-Demo).Count -eq 0) { Fallo "Falta DEMO_MESES en .env; esta carpeta no parece la de la práctica"; exit 1 }

if ($Completo) {
    & "$Raiz\demo\borrar_capa.ps1" oro -Si
    & "$Raiz\demo\borrar_capa.ps1" plata -Si
}
$inicio = Get-Date
& "$Raiz\scripts_windows\estado.ps1"
& "$Raiz\scripts_windows\reconstruir.ps1" oro
$t = (Get-Date) - $inicio
Log ("Práctica terminada en {0} min {1} s" -f [int][math]::Floor($t.TotalMinutes), $t.Seconds)
