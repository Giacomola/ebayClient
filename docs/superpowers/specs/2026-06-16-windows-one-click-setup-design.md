# Windows: Ein-Klick-Einrichtung & Updates (Design)

Datum: 2026-06-16
Thema: Die App so einfach wie möglich auf dem Windows-PC des Vaters installieren,
laufen lassen und aktuell halten.

## Kontext

Heute gibt es einen Doppelklick-Starter (`Start.bat`), einen leisen Start ohne
Terminal (`Start-leise.vbs` + Desktop-Verknüpfung) und zwei Anleitungen
(`EINRICHTUNG-WINDOWS.md` = Abo-Weg, `Windows-Anleitung.txt` = API-Schlüssel-Weg).
Die Einrichtung erfolgt aber in vielen Handschritten mit echten Stolperfallen:

- Python muss von Hand installiert werden, inkl. leicht vergessenem Häkchen
  „Add python.exe to PATH".
- Für den Abo-Weg zusätzlich Claude Code per PowerShell installieren und `claude`
  einloggen; `claude` wird erst in einer **neuen** Konsole gefunden.
- Der Notfall-Pfad in `Start.bat` installiert `claude-agent-sdk` **nicht** mit.
- SmartScreen- und Firewall-Nachfragen.
- Die beiden Anleitungen widersprechen sich (Abo vs. API-Schlüssel).

## Entscheidungen (vom Nutzer bestätigt)

1. **Einrichtungsmodell:** Giacomo richtet einmalig **per Fernwartung** ein; der
   Vater nutzt danach nur das Desktop-Symbol.
2. **KI-Zugang:** **Abo (Claude Code)**, kein API-Schlüssel.
3. **Ansatz:** Ein **`Install.bat`**, das alles Automatisierbare in **einem
   Doppelklick** erledigt, plus ein **`Update.bat`**.
4. **Update-Weg:** `Update.bat` lädt das **ZIP des `main`-Branch** vom
   **öffentlichen** GitHub-Repo `Giacomola/ebayClient`, ersetzt nur Code-Dateien
   und behält private Daten.

### Was „One-Click" NICHT abdecken kann (ehrlich)

Zwei Schritte erfordern einen Menschen und bleiben manuell:
- **`claude`-Login** (Browser-Anmeldung von Anthropic – nicht skriptbar).
- **imgbb-Schlüssel** einmal einfügen + in den Einstellungen „Abo" wählen.

`Install.bat` automatisiert alles andere und **führt** zu diesen zwei Schritten hin.

## Ziele / Nicht-Ziele

**Ziele**
- Eine einzige Datei (`Install.bat`), die Giacomo remote doppelklickt.
- Keine „Add-to-PATH"-Falle mehr (Python wird still und korrekt installiert).
- Nach der Einrichtung: ein Desktop-Symbol mit Logo, kein sichtbares Terminal.
- Einfaches `Update.bat` für spätere Stände.
- Konsistente, widerspruchsfreie Anleitungen.

**Nicht-Ziele (bewusst weggelassen, YAGNI)**
- Echter `.exe`-Installer (Inno Setup/PyInstaller) – Overkill für eine einmalige
  Fernwartung, plus Code-Signatur-Aufwand.
- Mitgeliefertes „portables" Python im ZIP.
- Automatische Firewall-Regel (bräuchte Admin) – die einmalige Klick-Bestätigung
  „Zugriff zulassen" reicht.

## Komponenten

### 1. `Install.bat` (Giacomo, remote, einmalig)

Defensiv geschrieben: jeder Schritt meldet im Klartext, was passiert, und **bricht
bei Fehlern mit verständlicher Meldung ab** (kein stilles Weiterlaufen).

1. **Python sicherstellen.** Ist `py`/`python` vorhanden, überspringen. Sonst den
   offiziellen Installer per PowerShell herunterladen und **still** ausführen:
   `… /quiet InstallAllUsers=0 PrependPath=1 Include_launcher=1`. Kein Häkchen nötig.
   - **Heikles Detail (im Plan zu lösen):** Der aktualisierte PATH gilt erst in
     einer **neuen** Konsole. `Install.bat` spricht das frisch installierte Python
     daher über den festen Pfad an (`%LocalAppData%\Programs\Python\Python3xx\python.exe`)
     **oder** startet sich nach der Python-Installation in einer frischen Konsole neu.
2. **Arbeitsumgebung + Pakete.** `.venv` anlegen, `pip install -r requirements.txt`
   (enthält `claude-agent-sdk`). Der bisherige abgespeckte Notfall-Pfad wird so
   korrigiert, dass `claude-agent-sdk` **immer** mitkommt (sonst scheitert der Abo-Weg).
3. **Claude Code installieren.** `powershell -ExecutionPolicy Bypass -Command "irm
   https://claude.ai/install.ps1 | iex"` (Native Installer, kein Node.js).
4. **Desktop-Symbol mit Logo** anlegen (vorhandene Logik aus
   `Verknuepfung-auf-Desktop.ps1` aufrufen).
5. **App starten** und Browser auf `http://127.0.0.1:5050` öffnen.
6. **Zu den zwei menschlichen Schritten führen.** Den `claude`-Login anstoßen
   (sichtbares Fenster mit `claude`) und anschließend klar anzeigen:
   „Noch 2 Dinge: imgbb-Schlüssel eintragen und in Einstellungen ‚Abo' wählen."

### 2. App-Härtung

- `_find_claude_cli()` soll `claude` **zusätzlich** im Standard-Installpfad
  `%USERPROFILE%\.local\bin` suchen (nicht nur über `shutil.which`/PATH). So
  funktioniert der Start auch, bevor je eine neue Konsole offen war.
- Reiner Python-Anteil → **Unit-Test** für diese Suche (z. B. via gepatchtem
  Pfad/Umgebung), da `.bat`-Logik hier nicht automatisiert testbar ist.

### 3. `Update.bat` (Giacomo, remote, später)

1. Lädt `https://github.com/Giacomola/ebayClient/archive/refs/heads/main.zip`
   per PowerShell in einen Temp-Ordner und entpackt es.
2. Kopiert die Code-Dateien in den Projektordner, **ohne** private Daten zu
   überschreiben. Explizite Ausnahmeliste: `config.json`, `draft.json`, `cases\`,
   `.venv\`, `logs\` (und der außerhalb liegende Speicherordner ist ohnehin nicht betroffen).
3. `pip install -r requirements.txt` im `.venv` (zieht neue Pakete nach).
4. Hinweis: Die **Versionsanzeige oben links** („Stand: …") bestätigt nach einem
   Neuladen den neuen Stand.

**Voraussetzung:** Das Repo `Giacomola/ebayClient` muss **öffentlich** sein. Das ist
unbedenklich, weil Geheimnisse (`config.json`, `draft.json`) **gitignored** sind und
nicht im Repo liegen. Updates kommen aus dem **`main`-Branch** (Giacomo merged dort
seinen veröffentlichten Stand hinein).

### 4. Doku aufräumen

- `EINRICHTUNG-WINDOWS.md` auf den Ein-Klick-Weg umstellen: `Install.bat` statt der
  vielen Handschritte; die Fernwartungs-/Vorbereitungs-Punkte und die
  Fehlerbehebung bleiben, werden aber an `Install.bat`/`Update.bat` angepasst.
- `Windows-Anleitung.txt` (für den Vater, täglich) an den **Abo-Weg** angleichen und
  den widersprüchlichen API-Schlüssel-Teil entfernen. Tägliche Nutzung bleibt:
  Desktop-Symbol → Fotos → „Anzeige erstellen" → „Zur eBay-Sammeldatei hinzufügen".

### 5. Abnahme / Test

- Kein echtes Windows in dieser Umgebung verfügbar → `.bat`-Skripte werden
  **defensiv** geschrieben (klare Abbrüche, Klartext-Meldungen).
- **Durchspiel-Checkliste für die Fernwartung** (Teil der aktualisierten
  `EINRICHTUNG-WINDOWS.md`): frisches Python via `Install.bat`, `claude`-Login,
  ein echtes Buch von Foto bis CSV.
- Automatisierter Test nur für den reinen Python-Anteil (`_find_claude_cli()`).

## Risiken & Gegenmaßnahmen

| Risiko | Gegenmaßnahme |
|---|---|
| PATH erst in neuer Konsole aktiv | Python über festen Pfad ansprechen oder Skript neu starten |
| `claude` nach Install nicht gefunden | App sucht zusätzlich in `%USERPROFILE%\.local\bin` |
| SmartScreen-Warnung bei `Install.bat` | Giacomo bestätigt einmal „Weitere Informationen → Trotzdem ausführen" |
| Firewall-Nachfrage | einmal „Zugriff zulassen" (für Handy-Zugang); kein Admin nötig |
| Python-Installer-URL veraltet | feste, gepflegte Version (aktuelles 3.12.x); bei Release prüfen |
| Repo versehentlich mit Geheimnissen | bleibt durch `.gitignore` ausgeschlossen; vor „public" einmal prüfen |

## Offene Punkte (im Plan zu fixieren)

- Genaue **Python-Version** und Installer-URL (Vorschlag: aktuelles 3.12.x amd64).
- Tactic für das PATH-Problem: fester Pfad vs. Selbst-Neustart (im Plan entscheiden).
- Exakte Code-vs-Daten-Trennung in `Update.bat` (Ausnahmeliste oben als Basis).
