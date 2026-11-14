@echo off
rem Lanza 00_preparar.ps1 con PowerShell sin cambiar la politica de ejecucion del equipo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp000_preparar.ps1" %*
exit /b %ERRORLEVEL%
