@echo off
rem Lanza 04_bigquery.ps1 con PowerShell sin cambiar la politica de ejecucion del equipo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp004_bigquery.ps1" %*
exit /b %ERRORLEVEL%
