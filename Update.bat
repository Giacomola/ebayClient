@echo off
rem ============================================================
rem  Buch-Anzeigen-Helfer  -  Update (Windows)
rem  Holt den neuesten Stand vom main-Branch (oeffentliches GitHub-Repo),
rem  ersetzt nur Code-Dateien und frischt die Pakete auf. Private Daten
rem  bleiben unberuehrt: config.json, draft.json, cases\, .venv\, logs\.
rem  Voraussetzung: das Repo Giacomola/ebayClient ist oeffentlich.
rem  HINWEIS: Muss auf einem echten Windows einmal durchgespielt werden.
rem ============================================================
setlocal EnableExtensions
cd /d "%~dp0"
title Buch-Anzeigen-Helfer - Update
chcp 65001 >nul

set "ZIPURL=https://github.com/Giacomola/ebayClient/archive/refs/heads/main.zip"
set "ZIP=%TEMP%\bah-update.zip"
set "OUT=%TEMP%\bah-update"
set "SRC=%OUT%\ebayClient-main"

echo Update wird geladen ...
if exist "%OUT%" rmdir /s /q "%OUT%"
powershell -NoProfile -Command "try { Invoke-WebRequest -Uri '%ZIPURL%' -OutFile '%ZIP%' } catch { exit 1 }"
if errorlevel 1 ( echo FEHLER: Konnte das Update nicht laden. Internet/Repo pruefen. & pause & exit /b 1 )

echo Entpacken ...
powershell -NoProfile -Command "Expand-Archive -Force '%ZIP%' '%OUT%'"
if errorlevel 1 ( echo FEHLER: Konnte das Update nicht entpacken. & pause & exit /b 1 )
if not exist "%SRC%" ( echo FEHLER: Unerwarteter Aufbau des Update-Pakets. & pause & exit /b 1 )

echo Dateien werden aktualisiert ^(private Daten bleiben erhalten^) ...
rem /E = inkl. Unterordner; /XF/.XD schuetzen private Daten und das laufende Skript.
robocopy "%SRC%" "%CD%" /E /NFL /NDL /NJH /NJS /NP ^
  /XF config.json draft.json Update.bat ^
  /XD ".venv" "cases" "logs" ".git" >nul
rem robocopy: Exit-Code < 8 = Erfolg.
if errorlevel 8 ( echo FEHLER beim Kopieren der neuen Dateien. & pause & exit /b 1 )

echo Pakete werden aufgefrischt ...
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
)

rmdir /s /q "%OUT%" 2>nul
del "%ZIP%" 2>nul

echo.
echo Fertig. Bitte das Programm einmal neu starten ^(oder die Seite neu laden^).
echo Oben links zeigt 'Stand: ...' den neuen Datenstand.
pause
exit /b 0
