@echo off
rem Erstellt einmalig die Desktop-Verknuepfung mit Logo (ruft das PowerShell-Skript auf).
rem Einfach doppelklicken. Danach startet man das Programm ueber das Desktop-Symbol.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Verknuepfung-auf-Desktop.ps1"
echo.
pause
