@echo off
rem Lanza subir_bigquery.ps1 con PowerShell sin cambiar la politica de ejecucion del equipo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0subir_bigquery.ps1" %*
exit /b %ERRORLEVEL%
