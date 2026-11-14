@echo off
rem Lanza 03_oro.ps1 con PowerShell sin cambiar la politica de ejecucion del equipo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp003_oro.ps1" %*
exit /b %ERRORLEVEL%
