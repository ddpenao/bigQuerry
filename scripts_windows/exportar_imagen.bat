@echo off
rem Lanza exportar_imagen.ps1 con PowerShell sin cambiar la politica de ejecucion del equipo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0exportar_imagen.ps1" %*
exit /b %ERRORLEVEL%
