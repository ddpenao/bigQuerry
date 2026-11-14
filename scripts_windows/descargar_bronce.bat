@echo off
rem Lanza descargar_bronce.ps1 con PowerShell sin cambiar la politica de ejecucion del equipo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0descargar_bronce.ps1" %*
exit /b %ERRORLEVEL%
