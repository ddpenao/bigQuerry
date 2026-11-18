@echo off
rem Lanza estado.ps1 con PowerShell sin cambiar la politica de ejecucion del equipo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0estado.ps1" %*
exit /b %ERRORLEVEL%
