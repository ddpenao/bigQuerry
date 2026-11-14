# PASO 0: esquema de cada archivo + muestra aleatoria de 1.000 filas. No modifica nada.
. "$PSScriptRoot\comun.ps1"
Log "PASO 0 - Reconocimiento de la capa bronce"
Salir-SiFallo (En-Contenedor tlc.reconocimiento) "El reconocimiento"
Log "Reporte: reportes\reconocimiento.md"
