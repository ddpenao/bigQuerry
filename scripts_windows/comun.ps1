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

# ---------- Rutas y estado de las capas ----------
function Ruta-Bronce  { $v = Leer-Env "RUTA_BRONCE_HOST"; if ($v) { $v } else { "../TLC" } }
function Bronce-Desde { $v = Leer-Env "BRONCE_DESDE"; if ($v) { $v } else { "2024-01" } }
function Bronce-Hasta { $v = Leer-Env "BRONCE_HASTA"; if ($v) { $v } else { "2026-08" } }

# Todos los meses AAAA-MM entre BRONCE_DESDE y BRONCE_HASTA
function Meses-Esperados {
    $m = [datetime]::ParseExact("$(Bronce-Desde)-01", "yyyy-MM-dd", $null)
    $fin = [datetime]::ParseExact("$(Bronce-Hasta)-01", "yyyy-MM-dd", $null)
    while ($m -le $fin) { $m.ToString("yyyy-MM"); $m = $m.AddMonths(1) }
}

# Meses sin su Parquet en bronce
function Meses-FaltantesBronce {
    $bronce = Ruta-Bronce
    foreach ($m in @(Meses-Esperados)) {
        $f = Get-ChildItem -Path $bronce -Recurse -Filter "yellow_tripdata_$m.parquet" -ErrorAction SilentlyContinue |
             Where-Object { $_.Length -gt 0 } | Select-Object -First 1
        if (-not $f) { $m }
    }
}

# Meses de plata que no tienen todos sus días
function Meses-IncompletosPlata {
    foreach ($m in @(Meses-Esperados)) {
        $dias = @(Get-ChildItem -Path "plata\viajes" -Directory -Filter "fecha=$m-*" -ErrorAction SilentlyContinue).Count
        $esperados = [datetime]::DaysInMonth([int]$m.Substring(0, 4), [int]$m.Substring(5, 2))
        if ($dias -lt $esperados) { $m }
    }
}

function Tablas-OroFaltantes {
    foreach ($t in "oro_kpi_mensual", "oro_kpi_anual", "oro_categoria_mensual", "oro_categoria_anual") {
        if (-not (Test-Path "oro\parquet\$t\part-*.parquet")) { $t }
    }
}

# Crea las carpetas ANTES de abrir el contenedor, para que Docker no las cree por su cuenta
function Asegurar-Carpetas {
    foreach ($c in "plata", "oro", "logs", "reportes", "datos_referencia", "credenciales", (Ruta-Bronce)) {
        New-Item -ItemType Directory -Force -Path $c | Out-Null
    }
}

# Ejecuta un módulo de Python dentro del contenedor y devuelve su código de salida.
# Es una función simple (sin param) para que opciones como --solo-oro pasen tal cual.
# La salida va directo a pantalla (Out-Host) y la función solo devuelve el código.
function En-Contenedor {
    Requiere-Env
    Asegurar-Carpetas
    & docker compose run --rm pipeline python -m @args | Out-Host
    return [int]$LASTEXITCODE
}

function Salir-SiFallo([int]$Codigo, [string]$Paso) {
    if ($Codigo -ne 0) {
        Fallo "$Paso terminó con error (código $Codigo). Revisa la carpeta logs\"
        exit $Codigo
    }
}
