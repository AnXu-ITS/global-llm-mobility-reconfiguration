@echo off
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0..\overleaf\scripts\build.ps1" -ExportFigures
pause
