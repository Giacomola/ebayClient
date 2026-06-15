@echo off
rem ============================================================
rem  Buch-Anzeigen-Helfer  -  Ein-Klick-Einrichtung (Windows, Abo-Weg)
rem  Einmal per Fernwartung doppelklicken. Installiert Python (still),
rem  Pakete, Claude Code, legt das Desktop-Symbol an und fuehrt zu den
rem  zwei Restschritten, die nur ein Mensch erledigen kann
rem  (claude-Login + imgbb-Schluessel).
rem  Umlaute in .bat sind heikel -> bewusst ae/oe/ue/ss.
rem  HINWEIS: Muss auf einem echten Windows einmal durchgespielt werden.
rem ============================================================
setlocal EnableExtensions
cd /d "%~dp0"
title Buch-Anzeigen-Helfer - Einrichtung
chcp 65001 >nul

echo ============================================================
echo   Buch-Anzeigen-Helfer  -  Einrichtung (einmalig)
echo ============================================================
echo.

rem --- 1) Python + Arbeitsumgebung ---------------------------------------
echo [1/5] Python und Arbeitsumgebung werden eingerichtet ...
if not exist ".venv\Scripts\python.exe" (
  call :setup_venv
  if errorlevel 1 (
    echo FEHLER: Python/Arbeitsumgebung. Internetverbindung pruefen und bei Giacomo melden.
    pause & exit /b 1
  )
)
echo     ok.
echo.

rem --- 2) Pakete ---------------------------------------------------------
echo [2/5] Pakete werden installiert ...
".venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
".venv\Scripts\python.exe" -m pip install --quiet -r requirements.txt
if errorlevel 1 (
  echo     Sammelinstallation hakte - installiere Kernpakete einzeln ...
  ".venv\Scripts\python.exe" -m pip install --quiet Flask anthropic requests qrcode claude-agent-sdk
  if errorlevel 1 ( echo FEHLER: Pakete konnten nicht installiert werden. & pause & exit /b 1 )
)
echo     ok.
echo.

rem --- 3) Claude Code (Abo-Weg) ------------------------------------------
echo [3/5] Claude Code wird installiert ...
set "CLAUDE=%USERPROFILE%\.local\bin\claude.exe"
if not exist "%CLAUDE%" powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://claude.ai/install.ps1 | iex"
if not exist "%CLAUDE%" echo     WARNUNG: 'claude' nicht am erwarteten Ort gefunden - der Login unten kann haken.
echo     ok.
echo.

rem --- 4) Desktop-Symbol -------------------------------------------------
echo [4/5] Desktop-Symbol mit Logo wird angelegt ...
powershell -NoProfile -ExecutionPolicy Bypass -File "Verknuepfung-auf-Desktop.ps1" >nul 2>nul
echo     ok.
echo.

rem --- 5) Zwei Restschritte (nur von Hand) -------------------------------
echo [5/5] Jetzt die zwei Schritte, die nur ein Mensch machen kann:
echo.
echo   A^) CLAUDE-LOGIN: Gleich oeffnet sich die Anmeldung im Browser.
echo      Mit dem Claude-Konto anmelden, das das Abo hat.
echo      Danach im schwarzen Fenster '/exit' eingeben oder es schliessen.
echo.
pause
if exist "%CLAUDE%" "%CLAUDE%"

echo.
echo   B^) Das Programm startet jetzt. Im Browser dann:
echo      - oben rechts 'Einstellungen' -^> Rechenleistung 'Claude-Abo' waehlen
echo      - imgbb-Schluessel eintragen -^> Speichern
echo.
pause
start "" ".venv\Scripts\pythonw.exe" app.py
timeout /t 2 >nul
start "" "http://127.0.0.1:5050"

echo.
echo Fertig. Ab jetzt genuegt das Desktop-Symbol 'Buch-Anzeigen-Helfer'.
echo Dieses Fenster kann geschlossen werden.
pause
exit /b 0

rem ====================================================================
rem  Unterprogramm: Python finden oder still installieren, dann .venv bauen
rem  Rueckgabe: errorlevel 0 = ok, 1 = Fehler
rem ====================================================================
:setup_venv
  set "PYLAUNCH="
  where py >nul 2>nul && set "PYLAUNCH=py -3"
  if not defined PYLAUNCH ( where python >nul 2>nul && set "PYLAUNCH=python" )
  if defined PYLAUNCH goto :makevenv

  echo     Python wird still installiert ^(ein bis zwei Minuten^) ...
  set "PYINST=%TEMP%\python-setup.exe"
  powershell -NoProfile -Command "try { Invoke-WebRequest 'https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe' -OutFile '%PYINST%' } catch { exit 1 }"
  if errorlevel 1 exit /b 1
  rem Still und ohne Admin (pro Benutzer), inkl. PATH - kein Haeckchen noetig.
  "%PYINST%" /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1 Include_test=0
  rem Frisch installiertes Python ueber den festen Benutzerpfad ansprechen,
  rem weil der neue PATH erst in einer neuen Konsole gilt.
  set "PYEXE="
  for /d %%D in ("%LocalAppData%\Programs\Python\Python3*") do set "PYEXE=%%D\python.exe"
  if not exist "%PYEXE%" exit /b 1
  set PYLAUNCH="%PYEXE%"

:makevenv
  %PYLAUNCH% -m venv .venv
  exit /b %errorlevel%
