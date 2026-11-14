# Funciones compartidas por los scripts de Windows. No se ejecuta solo.
# Compatible con Windows PowerShell 5.1 y PowerShell 7.
# "Continue": en PowerShell 5.1 con "Stop", cualquier aviso que docker o git escriban por
# stderr detendría el script. Los errores se revisan con $LASTEXITCODE.
$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"
$Raiz = Split-Path -Parent $PSScriptRoot
Set-Location $Raiz

function Log([string]$Texto)   { Write-Host ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Texto) -ForegroundColor Cyan }
function Fallo([string]$Texto) { Write-Host "[ERROR] $Texto" -ForegroundColor Red }

function Requiere-Env {
    if (-not (Test-Path ".env")) {
        Fallo "Falta el archivo .env. Ejecuta primero: scripts_windows\00_preparar.bat"
        exit 1
    }
}

# Lee una variable del archivo .env (devuelve "" si no existe)
function Leer-Env([string]$Nombre) {
    if (-not (Test-Path ".env")) { return "" }
    $linea = Get-Content ".env" | Where-Object { $_ -match "^$Nombre=" } | Select-Object -Last 1
    if (-not $linea) { return "" }
    return ($linea -replace "^$Nombre=", "").Trim()
}

# Escribe texto con saltos de línea LF y UTF-8 sin BOM (docker compose lo necesita así)
function Escribir-TextoLF([string]$Ruta, [string]$Texto) {
    $Texto = $Texto -replace "`r`n", "`n"
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText((Join-Path $Raiz $Ruta), $Texto, $utf8)
}

# Ejecuta un módulo de Python dentro del contenedor y devuelve su código de salida.
# Es una función simple (sin param) para que opciones como --solo-oro pasen tal cual.
# La salida va directo a pantalla (Out-Host) y la función solo devuelve el código.
function En-Contenedor {
    Requiere-Env
    & docker compose run --rm pipeline python -m @args | Out-Host
    return [int]$LASTEXITCODE
}

function Salir-SiFallo([int]$Codigo, [string]$Paso) {
    if ($Codigo -ne 0) {
        Fallo "$Paso terminó con error (código $Codigo). Revisa la carpeta logs\"
        exit $Codigo
    }
}
