@echo off
rem Doppelklick-Start fuer Windows. Richtet beim ersten Mal alles selbst ein und
rem oeffnet danach den Browser. Umlaute werden in .bat-Dateien oft falsch angezeigt,
rem darum hier bewusst ae/oe/ue/ss.
setlocal EnableExtensions
cd /d "%~dp0"
title Buch-Anzeigen-Helfer
rem UTF-8, damit der QR-Code (Block-Zeichen) im Fenster sauber dargestellt wird
chcp 65001 >nul

echo Buch-Anzeigen-Helfer wird gestartet ...
echo.

rem --- Python suchen: erst der Launcher "py", dann "python" ---
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo Python wurde nicht gefunden.
  echo.
  echo Bitte installiere Python von der Webseite, die sich jetzt oeffnet.
  echo WICHTIG: Beim Installieren das Haeckchen "Add python.exe to PATH" setzen!
  echo Danach diese Datei ^(Start.bat^) einfach erneut doppelklicken.
  start "" "https://www.python.org/downloads/"
  echo.
  pause
  exit /b 1
)

rem --- Beim ersten Start: virtuelle Umgebung anlegen und Pakete installieren ---
if not exist ".venv\Scripts\python.exe" (
  echo Erste Einrichtung - das dauert einmalig ein bis zwei Minuten ...
  %PY% -m venv .venv
  if errorlevel 1 (
    echo Konnte die Arbeitsumgebung nicht anlegen.
    pause
    exit /b 1
  )
  ".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
  ".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
  if errorlevel 1 (
    echo Vollstaendige Installation fehlgeschlagen - versuche die Kernpakete ...
    ".venv\Scripts\python.exe" -m pip install --quiet Flask anthropic requests
    if errorlevel 1 (
      echo Installation fehlgeschlagen. Bitte Internetverbindung pruefen und erneut versuchen.
      pause
      exit /b 1
    )
  )
)

echo.
echo Fertig. Der Browser oeffnet sich gleich von selbst.
echo Dieses schwarze Fenster bitte offen lassen, solange du das Programm nutzt.
echo Zum Beenden einfach dieses Fenster schliessen.
echo.
".venv\Scripts\python.exe" app.py
pause
