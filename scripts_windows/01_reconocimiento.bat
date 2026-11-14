@echo off
rem Lanza 01_reconocimiento.ps1 con PowerShell sin cambiar la politica de ejecucion del equipo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp001_reconocimiento.ps1" %*
exit /b %ERRORLEVEL%
