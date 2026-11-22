@echo off
rem Lanza borrar_capa.ps1 con PowerShell sin cambiar la politica de ejecucion del equipo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0borrar_capa.ps1" %*
exit /b %ERRORLEVEL%
