@echo off
rem Lanza 05_consulta_bq.ps1 con PowerShell sin cambiar la politica de ejecucion del equipo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp005_consulta_bq.ps1" %*
exit /b %ERRORLEVEL%
