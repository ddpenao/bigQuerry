# Deja todo listo: .env, carpetas, tabla de zonas, imagen Docker y repositorio git.
. "$PSScriptRoot\comun.ps1"

Log "1/6 Verificando Docker y git"
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Fallo "Docker no está instalado (instala Docker Desktop)"; exit 1 }
& docker info *> $null
if ($LASTEXITCODE -ne 0) { Fallo "Docker no responde. Abre Docker Desktop y espera a que diga 'Engine running'"; exit 1 }
& docker compose version *> $null
if ($LASTEXITCODE -ne 0) { Fallo "Falta 'docker compose'"; exit 1 }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Fallo "git no está instalado (https://git-scm.com)"; exit 1 }

Log "2/6 Archivo .env"
if (-not (Test-Path ".env")) {
    Escribir-TextoLF ".env" ([System.IO.File]::ReadAllText((Join-Path $Raiz "plantilla_env.txt")))
    Log "   .env creado desde plantilla_env.txt"
}

Log "3/6 Carpetas de trabajo"
foreach ($c in "plata", "oro", "logs", "reportes", "datos_referencia", "credenciales") {
    New-Item -ItemType Directory -Force -Path $c | Out-Null
}

Log "4/6 Capa bronce (solo lectura)"
$bronce = Leer-Env "RUTA_BRONCE_HOST"
if (-not $bronce) { $bronce = "../TLC" }
$archivos = @()
if (Test-Path $bronce) { $archivos = @(Get-ChildItem -Path $bronce -Recurse -Filter "yellow_tripdata_*.parquet") }
if ($archivos.Count -eq 0) {
    Fallo "No encontré archivos yellow_tripdata_*.parquet en $bronce"
    Fallo "Descárgalos con: scripts_windows\descargar_bronce.bat  (o revisa RUTA_BRONCE_HOST en .env)"
    exit 1
}
Log "   $($archivos.Count) archivos Parquet en $bronce"

Log "5/6 Tabla de zonas de TLC (para la dimensión distrito)"
$zonas = "datos_referencia\taxi_zone_lookup.csv"
if ((Test-Path $zonas) -and (Get-Item $zonas).Length -gt 0) {
    Log "   ya existe $zonas"
} else {
    try {
        Invoke-WebRequest -UseBasicParsing -Uri "https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv" -OutFile $zonas -ErrorAction Stop
        Log "   descargada: $((Get-Content $zonas).Count - 1) zonas"
    } catch {
        Remove-Item $zonas -ErrorAction SilentlyContinue
        Fallo "No se pudo descargar. El pipeline sigue funcionando, pero sin distrito_origen."
    }
}

Log "6/6 Imagen Docker (la primera vez tarda varios minutos)"
& docker compose build
Salir-SiFallo $LASTEXITCODE "La construcción de la imagen"

if (-not (Test-Path ".git")) {
    & git init -b main | Out-Null
    Log "   repositorio git inicializado (rama main)"
}
Log "Listo. Siguiente paso: scripts_windows\ejecutar_todo.bat"
