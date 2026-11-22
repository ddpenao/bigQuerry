@echo off
rem Lanza preparar_demo.ps1 con PowerShell sin cambiar la politica de ejecucion del equipo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0preparar_demo.ps1" %*
exit /b %ERRORLEVEL%
