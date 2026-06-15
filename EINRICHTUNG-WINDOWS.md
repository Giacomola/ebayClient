# Einrichtung auf einem Windows-PC (per Fernwartung)

Anleitung für **dich als Einrichter** – Schritt für Schritt zum Abhaken.
Zielsystem: **Windows 10/11 (64-Bit)**, KI-Weg: **Claude-Abo** (kein API-Schlüssel).

> Reihenfolge ist wichtig: Erst **Claude Code installieren + einloggen**, dann das
> Programm starten. Sonst findet der Abo-Weg den Befehl `claude` nicht.

---

## 0. Vorbereitung (VOR der Fernwartung erledigen – spart Zeit)

- [ ] **Fernwartung** bereit (TeamViewer oder AnyDesk auf beiden PCs).
- [ ] **Claude-Abo** vorhanden und Zugangsdaten zur Hand (Pro oder Max).
      Ohne aktives Abo gibt es kein Monatsguthaben → der Abo-Weg funktioniert nicht.
- [ ] **imgbb-Schlüssel** erstellen (kostenlos, für den Foto-Upload):
      [api.imgbb.com](https://api.imgbb.com) → Konto → „Get API Key" → Schlüssel notieren.
- [ ] **Projektordner zum Übertragen vorbereiten:** den Ordner `ebay-client`
      kopieren, dabei den Unterordner **`.venv` löschen** (ist groß und Mac-spezifisch,
      wird auf Windows neu gebaut). `config.json` ebenfalls weglassen.
      Den Rest als ZIP packen → per Fernwartung-Dateiübertragung oder Cloud rüberschieben.

---

## 1. Python installieren

1. [ ] Auf dem Windows-PC **`Start.bat`** doppelklicken (liegt im Projektordner).
   - Erscheint die Warnung „Der Computer wurde durch Windows geschützt":
     **„Weitere Informationen" → „Trotzdem ausführen"**.
2. [ ] Fehlt Python, öffnet sich automatisch die Download-Seite.
   - Python installieren und dabei **unbedingt das Häkchen „Add python.exe to PATH"** setzen.
3. [ ] Nach der Installation **`Start.bat` erneut** doppelklicken.

✓ Geschafft, wenn das schwarze Fenster „Erste Einrichtung …" zeigt (Pakete werden geladen).
Das kann 1–2 Minuten dauern. **Dieses Fenster offen lassen.**

> Falls die Installation mittendrin abbricht: siehe **Fehlerbehebung → A**.

---

## 2. Claude Code installieren (der Kern des Abo-Wegs)

1. [ ] **PowerShell** öffnen: Startmenü → „PowerShell" eintippen → öffnen.
2. [ ] Diesen Befehl eingeben und Enter:
   ```
   irm https://claude.ai/install.ps1 | iex
   ```
   (Native Installer von Anthropic – **kein Node.js nötig**.)
3. [ ] **PowerShell schließen und neu öffnen** (wichtig, damit der Befehl `claude` gefunden wird).

✓ Test: `claude --version` eingeben → es kommt eine Versionsnummer.

> Kommt „claude wird nicht erkannt": siehe **Fehlerbehebung → B**.

---

## 3. Bei Claude einloggen (mit dem Abo)

1. [ ] In PowerShell eingeben:
   ```
   claude
   ```
2. [ ] Es öffnet sich der Browser → mit **dem Claude-Konto, das das Abo hat**, anmelden.
3. [ ] Wenn Claude Code den Chat-Prompt zeigt, ist der Login fertig.
   Mit `/exit` (oder Fenster schließen) wieder raus.

✓ Geschafft, wenn der Login ohne Fehler durchläuft. Der Login bleibt gespeichert –
das Programm nutzt ihn künftig im Hintergrund.

---

## 4. Programm starten

1. [ ] **`Start.bat`** doppelklicken (falls nicht mehr offen).
2. [ ] Der Browser öffnet sich von selbst auf **http://127.0.0.1:5050**.
   - Das schwarze Fenster muss **offen bleiben**, solange das Programm läuft.

✓ Geschafft, wenn die Seite „Buch-Anzeigen-Helfer" im Browser steht.

---

## 5. In der App einrichten

1. [ ] Oben rechts **„Einstellungen"**.
2. [ ] **Rechenleistung → „Claude-Abo (Monatsguthaben, kein Schlüssel nötig)"** wählen.
       (Den Anthropic-API-Schlüssel **leer lassen** – wird beim Abo-Weg nicht gebraucht.)
3. [ ] **imgbb-Schlüssel** eintragen (aus Schritt 0).
4. [ ] **Speichern**.
5. [ ] Unten einmal **„Ordner wählen"** → einen einfachen Ordner festlegen
       (z. B. Desktop → neuer Ordner „eBay-Anzeigen"). Dort landen die CSV-Dateien.

---

## 6. Funktionstest (ein echtes Buch durchspielen)

1. [ ] Ein, zwei **Fotos eines Buches** in die Ablagefläche ziehen.
2. [ ] **„Anzeige erstellen"** → 30–60 Sek. warten (die KI recherchiert).
3. [ ] Felder erscheinen und sind ausgefüllt → der Abo-Weg funktioniert. ✓
4. [ ] **„Zur eBay-Sammeldatei hinzufügen"** → Erfolgsmeldung + „Eintrag anzeigen".
5. [ ] „Eintrag anzeigen" öffnet die CSV (z. B. in Excel) → alles da. ✓

Wenn das klappt, ist die Einrichtung komplett.

---

## 6b. Desktop-Verknüpfung mit Logo anlegen (ohne Terminal)

Damit dein Vater künftig **nur ein Symbol mit Logo** anklickt und **kein schwarzes
Fenster** mehr aufgeht:

1. [ ] Im Projektordner **`Verknuepfung-auf-Desktop.cmd`** doppelklicken.
   - Es erscheint kurz ein Fenster und meldet „Verknüpfung … liegt jetzt auf dem Desktop".
2. [ ] Auf dem Desktop liegt nun das Symbol **„Buch-Anzeigen-Helfer"** mit dem Logo.
3. [ ] **Test:** Doppelklick darauf → der Browser öffnet sich, **kein Terminal**.

> Technik dahinter: Das Symbol startet `Start-leise.vbs`, das die App über
> `pythonw.exe` (Python ohne Konsole) unsichtbar im Hintergrund laufen lässt.
> Die einmalige Erstinstallation (Schritt 4 mit `Start.bat`) muss **vorher** gelaufen
> sein – sonst springt der leise Start automatisch auf den sichtbaren Einrichter um.
>
> Wichtig: Den **Projektordner danach nicht mehr verschieben/umbenennen** – die
> Verknüpfung merkt sich den festen Pfad. Falls doch verschoben, einfach
> `Verknuepfung-auf-Desktop.cmd` erneut ausführen.

---

## 7. Tägliche Nutzung (kurz für deinen Vater erklären)

1. **Desktop-Symbol „Buch-Anzeigen-Helfer"** doppelklicken → Browser öffnet sich
   (kein schwarzes Fenster mehr).
2. Fotos reinziehen → **„Anzeige erstellen"** → prüfen/anpassen.
3. **„Zur eBay-Sammeldatei hinzufügen"**.
4. Wenn alle Bücher drin sind: die **CSV bei eBay hochladen** (File-Exchange).
5. Danach in der App **„Als zu eBay hochgeladen markieren"** (damit nichts doppelt hochgeladen wird).
6. Beenden: unten auf der Seite **„Programm beenden"** (es läuft ja unsichtbar im
   Hintergrund – darum gibt es kein Fenster zum Schließen).

---

## Fehlerbehebung

**A) Erstinstallation der Pakete schlägt fehl (oder Abo-Weg meldet „braucht claude-agent-sdk")**
Die Notfall-Variante von `Start.bat` lädt nur Flask/anthropic/requests – dabei fehlt
`claude-agent-sdk`. Einmal von Hand nachinstallieren: im Projektordner ein
Eingabe­aufforderungs-Fenster öffnen (Adressleiste des Ordners → `cmd` eintippen) und:
```
.venv\Scripts\python.exe -m pip install claude-agent-sdk
```

**B) „claude wird nicht erkannt" / App meldet „Befehl 'claude' nicht gefunden"**
- PowerShell **neu öffnen** (oder PC neu starten) – der Pfad muss erst übernommen werden.
- Prüfen, ob `%USERPROFILE%\.local\bin` im PATH steht.
- Erneut testen: `claude --version`.
- Danach `Start.bat` neu starten (das Programm sucht `claude` beim Start).

**C) Die Seite öffnet sich nicht**
Im Browser von Hand **http://127.0.0.1:5050** eingeben. Das schwarze Fenster muss laufen.

**D) „Anzeige erstellen" hängt sehr lange / bricht ab**
Der Abo-Weg sucht im Netz; das dauert 30–60 Sek. Bei Abbruch erneut klicken.
Hält es dauerhaft an, Internetverbindung prüfen und `Start.bat` neu starten.

**E) macOS-Datei `Buch-Anzeigen-Helfer.app`**
Die ist **nur für Mac** – unter Windows ignorieren und immer **`Start.bat`** nutzen.

---

## Konten-/Schlüssel-Übersicht (was wofür)

| Was | Wofür | Kosten |
|---|---|---|
| Claude-Abo (Pro/Max) | KI-Texte über das Monatsguthaben | im Abo enthalten |
| imgbb-Schlüssel | Fotos ins Netz laden (für die CSV) | kostenlos |
| eBay-Konto | die fertige CSV hochladen | eBay-übliche Gebühren |
