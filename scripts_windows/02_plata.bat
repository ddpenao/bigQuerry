@echo off
rem Lanza 02_plata.ps1 con PowerShell sin cambiar la politica de ejecucion del equipo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp002_plata.ps1" %*
exit /b %ERRORLEVEL%
