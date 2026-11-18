@echo off
rem Lanza reconstruir.ps1 con PowerShell sin cambiar la politica de ejecucion del equipo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0reconstruir.ps1" %*
exit /b %ERRORLEVEL%
