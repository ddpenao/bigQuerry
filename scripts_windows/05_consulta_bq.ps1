# Consulta BigQuery con dry run obligatorio y bloqueo de SELECT *.
#   scripts_windows\05_consulta_bq.bat "SELECT periodo, viajes FROM `PROYECTO.tlc_taxis.oro_kpi_mensual` LIMIT 5"
#   scripts_windows\05_consulta_bq.bat --solo-estimar "SELECT ..."
. "$PSScriptRoot\comun.ps1"
if ($args.Count -lt 1) { Fallo 'Uso: 05_consulta_bq.bat [--solo-estimar] "SQL"'; exit 1 }
$opciones = @($args)
exit (En-Contenedor tlc.bigquery_seguro @opciones)
