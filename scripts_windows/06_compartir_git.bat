@echo off
rem Lanza 06_compartir_git.ps1 con PowerShell sin cambiar la politica de ejecucion del equipo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp006_compartir_git.ps1" %*
exit /b %ERRORLEVEL%
