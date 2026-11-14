@echo off
rem Lanza ejecutar_todo.ps1 con PowerShell sin cambiar la politica de ejecucion del equipo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0ejecutar_todo.ps1" %*
exit /b %ERRORLEVEL%
