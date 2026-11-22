# Borra una capa de la PRÁCTICA (nunca la del proyecto completo ni ..\TLC).
#   demo\borrar_capa.bat bronce | plata | oro     (pide confirmación)
#   demo\borrar_capa.bat plata -Si                 (sin preguntar)
param([string]$Capa = "", [switch]$Si)
. "$PSScriptRoot\..\scripts_windows\comun.ps1"
if (@(Meses-Demo).Count -eq 0) { Fallo "Esta carpeta no es la de la práctica (falta DEMO_MESES en .env). No borro nada."; exit 1 }

switch ($Capa) {
    "bronce" { $objetivo = "bronce_demo" }
    "plata"  { $objetivo = "plata" }
    "oro"    { $objetivo = "oro" }
    default  { Fallo "Uso: demo\borrar_capa.bat bronce|plata|oro [-Si]"; exit 1 }
}
$ruta = [System.IO.Path]::GetFullPath((Join-Path $Raiz $objetivo))
if (-not $ruta.StartsWith($Raiz + [System.IO.Path]::DirectorySeparatorChar, [System.StringComparison]::OrdinalIgnoreCase)) {
    Fallo "Ruta fuera de la carpeta de la práctica: $ruta"; exit 1
}
if (-not $Si) {
    $r = Read-Host "Se borrará $ruta. ¿Continuar? (s/N)"
    if ($r -notmatch '^[sS]$') { Log "Cancelado"; exit 0 }
}
if (Test-Path $ruta) { Get-ChildItem -Path $ruta -Force | Remove-Item -Recurse -Force }
New-Item -ItemType Directory -Force -Path $ruta | Out-Null
Log "Capa $Capa de la práctica borrada ($ruta)"
