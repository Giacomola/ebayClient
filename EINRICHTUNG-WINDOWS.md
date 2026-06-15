# Einrichtung auf einem Windows-PC (per Fernwartung)

Anleitung für **dich als Einrichter** – Schritt für Schritt zum Abhaken.
Zielsystem: **Windows 10/11 (64-Bit)**, KI-Weg: **Claude-Abo** (kein API-Schlüssel).

> Neu: Die Einrichtung läuft jetzt fast vollständig über **einen Doppelklick**
> (`Install.bat`). Nur zwei Dinge muss ein Mensch tun (Claude-Login + imgbb-Schlüssel) –
> die kann kein Skript übernehmen.

---

## 0. Vorbereitung (VOR der Fernwartung erledigen – spart Zeit)

- [ ] **Fernwartung** bereit (TeamViewer oder AnyDesk auf beiden PCs).
- [ ] **Claude-Abo** vorhanden und Zugangsdaten zur Hand (Pro oder Max).
      Ohne aktives Abo gibt es kein Monatsguthaben → der Abo-Weg funktioniert nicht.
- [ ] **imgbb-Schlüssel** erstellen (kostenlos, für den Foto-Upload):
      [api.imgbb.com](https://api.imgbb.com) → Konto → „Get API Key" → Schlüssel notieren.
- [ ] **Projektordner zum Übertragen vorbereiten:** den Ordner `ebay-client`
      kopieren, dabei den Unterordner **`.venv` löschen** (groß und Mac-spezifisch,
      wird auf Windows neu gebaut) und **`config.json` weglassen**. Den Rest als ZIP
      packen → per Fernwartung-Dateiübertragung oder Cloud rüberschieben und auspacken.
- [ ] *(Nur falls du später `Update.bat` nutzen willst:)* das GitHub-Repo
      `Giacomola/ebayClient` auf **public** stellen. Unbedenklich, weil `config.json`
      und `draft.json` per `.gitignore` **nicht** im Repo liegen.

---

## 1. Ein-Klick-Einrichtung

1. [ ] Im Projektordner **`Install.bat`** doppelklicken.
   - Erscheint „Der Computer wurde durch Windows geschützt":
     **„Weitere Informationen" → „Trotzdem ausführen"**.
2. [ ] Einfach laufen lassen. `Install.bat` erledigt der Reihe nach:
   - **Python** still installieren (kein „Add to PATH"-Häkchen nötig),
   - **Arbeitsumgebung + alle Pakete** (inkl. `claude-agent-sdk`),
   - **Claude Code** installieren,
   - **Desktop-Symbol mit Logo** anlegen.
   Das dauert beim ersten Mal ein paar Minuten. Bei einem Fehler **stoppt** es mit
   einer klaren Meldung (dann siehe **Fehlerbehebung**).

✓ Geschafft, wenn das Skript zu **„Schritt A) CLAUDE-LOGIN"** kommt.

---

## 2. Die zwei Schritte von Hand (führt dich `Install.bat` durch)

**A) Claude-Login** (für das Abo)
1. [ ] Wenn das Skript dazu auffordert, **Enter** drücken – es öffnet sich der Browser.
2. [ ] Mit **dem Claude-Konto anmelden, das das Abo hat**.
3. [ ] Im schwarzen Fenster danach **`/exit`** eingeben (oder es schließen).
   Der Login bleibt gespeichert; das Programm nutzt ihn künftig im Hintergrund.

**B) imgbb-Schlüssel + Abo wählen** (im Browser, die App startet automatisch)
1. [ ] Oben rechts **„Einstellungen"**.
2. [ ] **Rechenleistung → „Claude-Abo (Monatsguthaben, kein Schlüssel nötig)"**.
       (Den Anthropic-API-Schlüssel **leer lassen**.)
3. [ ] **imgbb-Schlüssel** eintragen (aus Schritt 0).
4. [ ] **Speichern**.
5. [ ] Unten **„Ordner wählen"** → einen einfachen Ordner festlegen
       (z. B. Desktop → neuer Ordner „eBay-Anzeigen"). Dort landen die CSV-Dateien.

---

## 3. Funktionstest (ein echtes Buch durchspielen)

1. [ ] Ein, zwei **Fotos eines Buches** in die Ablagefläche ziehen.
2. [ ] **„Anzeige erstellen"** → 30–60 Sek. warten (die KI recherchiert).
3. [ ] Felder erscheinen und sind ausgefüllt → der Abo-Weg funktioniert. ✓
4. [ ] **„Zur eBay-Sammeldatei hinzufügen"** → Erfolgsmeldung + „Eintrag anzeigen".
5. [ ] „Eintrag anzeigen" öffnet die CSV (z. B. in Excel) → alles da. ✓

Wenn das klappt, ist die Einrichtung komplett.

---

## 4. Tägliche Nutzung (kurz für deinen Vater)

1. **Desktop-Symbol „Buch-Anzeigen-Helfer"** doppelklicken → Browser öffnet sich
   (kein schwarzes Fenster).
2. Fotos reinziehen oder **„📱 Per Handy hochladen"** → **„Anzeige erstellen"** → prüfen.
3. **„Zur eBay-Sammeldatei hinzufügen"**.
4. Wenn alle Bücher drin sind: die **CSV bei eBay hochladen** (File-Exchange).
5. Beenden: unten auf der Seite **„Programm beenden"** (es läuft unsichtbar im
   Hintergrund – daher gibt es kein Fenster zum Schließen).

> Die ausführliche, seniorenfreundliche Version steht in **`Windows-Anleitung.txt`**.

---

## 5. Später: Updates einspielen

Wenn es eine neue Version gibt:

1. [ ] Im Projektordner **`Update.bat`** doppelklicken.
   - Es lädt den neuesten Stand aus dem **`main`-Branch** des öffentlichen Repos,
     ersetzt nur Code-Dateien und frischt die Pakete auf.
   - **Private Daten bleiben unberührt** (`config.json`, `draft.json`, `cases\`).
2. [ ] Programm einmal neu starten / Seite neu laden. **Oben links** zeigt „Stand: …"
       den neuen Datenstand.

> Voraussetzung: Das Repo ist **public** (siehe Schritt 0). Ist es privat, bringst du
> die neuen Dateien stattdessen per Fernwartung rüber und führst nur `Update.bat` aus
> (es frischt dann zumindest die Pakete auf).

---

## Fehlerbehebung

**A) `Install.bat` stoppt bei „Pakete"**
Internetverbindung prüfen und `Install.bat` erneut doppelklicken. Hilft das nicht,
im Projektordner ein cmd-Fenster öffnen (Adressleiste → `cmd`) und von Hand:
```
.venv\Scripts\python.exe -m pip install claude-agent-sdk
```

**B) „claude wird nicht erkannt" / App meldet „Befehl 'claude' nicht gefunden"**
- PC neu starten (oder neue Konsole) – der Pfad muss erst übernommen werden.
- Prüfen, ob `%USERPROFILE%\.local\bin\claude.exe` existiert.
- Das Programm sucht `claude` auch direkt an diesem Ort; sonst `Install.bat` erneut laufen lassen.

**C) Die Seite öffnet sich nicht**
Im Browser von Hand **http://127.0.0.1:5050** eingeben.

**D) „Anzeige erstellen" hängt lange / bricht ab**
Der Abo-Weg sucht im Netz; das dauert 30–60 Sek. Bei Abbruch erneut klicken.

**E) macOS-Datei `Buch-Anzeigen-Helfer.app`**
Die ist **nur für Mac** – unter Windows ignorieren und das **Desktop-Symbol** nutzen
(zur Erst-Einrichtung `Install.bat`).

---

## Konten-/Schlüssel-Übersicht (was wofür)

| Was | Wofür | Kosten |
|---|---|---|
| Claude-Abo (Pro/Max) | KI-Texte über das Monatsguthaben | im Abo enthalten |
| imgbb-Schlüssel | Fotos ins Netz laden (für die CSV) | kostenlos |
| eBay-Konto | die fertige CSV hochladen | eBay-übliche Gebühren |
