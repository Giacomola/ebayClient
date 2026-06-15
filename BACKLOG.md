# Backlog (geordnet)

**Nicht hier reinschreiben — wirf Wünsche in `INBOX.md`.** Diese Datei pflegt
Claude (aus der Inbox in die Tabs einsortieren, Status, Erledigt). Tippst du
hier doch, kann es mit Schreibzugriffen des Daemons kollidieren.

Workflow-Regeln: siehe `CLAUDE.md` → „Backlog-Workflow".
Konvention: offene Aufgaben tragen am Ende einen Code-Tag `` `→ datei` `` (von Claude gesetzt).

---

##### Discussion #####
_Claude verschiebt hierher Backlog-Punkte, die **unklar, schädlich oder klar nachteilig**
sind — mit `> Grund: …` — statt sie blind auszuführen. Du klärst: präzisieren und zurück in
den Tab, oder über `### Push` neu einreichen; Claude entfernt erledigte Punkte._

## 🚧 In Arbeit
_Claims. VOR dem Start hier eintragen (`` `datei` — Aufgabe — seit Zeit ``),
nach Abschluss entfernen._

## 📷 Eingabe/Fotos
_Fotos reinziehen, Ordnerwahl, Upload zu imgbb, Vorschau._

## ✍️ KI-Anzeigentext
_Claude-Generierung, Felder (Titel, Beschreibung, Merkmale), Preis, Zustand, Stilvorlage._



## 📄 CSV-Export
_eBay-File-Exchange-CSV erzeugen, Sammel-CSV, Zielordner, Feld-Grenzen._

## 💰 Preisvergleich
_Preis-Recherche, Vergleichsanzeigen, Suchlogik._


## ⚙️ Einstellungen
_API-Schlüssel (Anthropic, imgbb), Konfiguration, Speicherorte._

## 🌐 Allgemein
_Tab-übergreifend: Start/Beenden, App-Launcher, Tempo, Dokumentation._

## 🕓 Später (zurückgestellt)
_Bewusst auf später verschoben — nicht ohne Ansage starten._

---

## ✅ Erledigt
_Abgehakt, mit Datum + Commit. Verlauf, wird nicht gelöscht._

- [x] 2026-06-15 Rechenleistung-Schalter robust: Listener über on()-Helfer angehängt, ein fehlendes Element friert die Seite nicht mehr ein (app.js) `b54ebc5`.
- [x] 2026-06-15 Einstellungs-Schalter „Rechenleistung" (API-Schlüssel/Abo) in der Oberfläche (templates/index.html, app.js) `d921c02`.
- [x] 2026-06-15 Rechenleistung umschaltbar: KI-Analyse wahlweise über API-Schlüssel oder Claude-Abo (Agent SDK / Claude-Code-CLI) (web_ai.py, ai_client.py, price_analysis.py, app.py, config.py, requirements.txt) `b171a47`.
- [x] 2026-06-15 Fehlende Informationen nicht anzeigen: KI lässt unbekannte Pflichtangaben weg statt roten Platzhalter einzusetzen (anweisungen.txt).
- [x] 2026-06-15 DnB/DDB als bevorzugte Quelle im Recherche-Prompt verankert (anweisungen.txt).
- [x] 2026-06-15 Preis-Suchbegriff: erste 4 Wörter des Buchtitels + Jahr als empfohlene Suchanfrage (price_analysis.py).
- [x] 2026-06-15 Preisvergleich: Beispielpreise zeigen den Preis fett hervorgehoben + anklickbaren Link (app.js).
- [x] 2026-06-15 Zwei anklickbare Titelvorschläge (title + title_alt), Klick übernimmt den Titel (ai_client.py, index.html, app.js, style.css).
- [x] 2026-06-15 Strukturierte antiquarische Beispiel-Beschreibung in reinem HTML als Stil-Vorlage (anweisungen.txt).
- [x] 2026-06-15 Beschreibungs-Textfeld nutzt mehr Bildschirmhöhe (max-height 65vh) (style.css).
- [x] 2026-06-15 DNB/DDB als Primärquelle der Recherche, andere Quellen nur als Rückfall (anweisungen.txt).
- [x] 2026-06-15 Beschreibungs-Prompt exakt an die Beispiel-Vorlage angeglichen (jeder Punkt eigener <p>, <b> nur für Autor/Titel & „Zustand:"/„Zum Werk:"), Semikolon im Beispiel entfernt; config.py-Default synchron (anweisungen.txt, config.py).
- [x] 2026-06-15 Beschreibung aufgeteilt (#27+#28): Zustand & sichtbare/physische Beschreibung AUSSCHLIESSLICH aus den Fotos; „Zum Werk"/bibliografischer Teil darf aus Quellen (bevorzugt ZVAB). Datenquellen DNB/DDB/ZVAB gleichrangig (anweisungen.txt, config.py).
- [x] 2026-06-15 Preisrecherche startet automatisch, sobald der Text fertig ist (app.js).
- [x] 2026-06-15 Knopf „Sammeldatei archivieren & neu beginnen": benennt die aktive Datei in eBayClient_<Datum>[_Name].csv um (Name manuell, Datum immer vorangestellt), danach beginnt die Sammeldatei neu. Ersetzt den alten „Als hochgeladen markieren"-Knopf (ebay_csv.py, app.py, index.html, app.js, Tests).
- [x] 2026-06-15 Alle Links der Seite öffnen in einem neuen Tab/Fenster (global via <base target="_blank">) (index.html).
- [x] 2026-06-15 Senioren-/Einrichter-Anleitung für Windows per Fernwartung (Abo-Weg) + App-Icon fürs Windows-Paket (EINRICHTUNG-WINDOWS.md, app.ico).
- [x] 2026-06-15 Inhaltsbreite per ↔−/↔+ in der Kopfzeile verstellbar (Stufen 720/900/1100/1400 px, im Browser gespeichert wie die Schriftgröße); CSS-Variable --page-width (index.html, app.js, style.css).
- [x] 2026-06-15 Handy-Zugang per QR-Code im Browser (Route /api/handy-zugang liefert WLAN-Adresse + QR als SVG, Knopf „Per Handy hochladen") (app.py, app.js, style.css, index.html, Tests) `ac7b55b`.
- [x] 2026-06-15 Verständliche Fehlermeldung bei Token-/Anfrage-Limit (429) und zu großer Eingabe (400 „prompt too long" → 413); gemeinsame Hilfsfunktion _ki_fehlerantwort für alle KI-Routen (app.py, Tests).
- [x] 2026-06-15 Bei mehr als 2 Fotos auswählbar, welche analysiert werden (🔍-Häkchen je Bild, erste 3 vorausgewählt, höchstens 5); alle Fotos kommen weiterhin in die Anzeige. Backend kappt defensiv bei 5 (app.py, index.html, app.js, Tests).
- [x] 2026-06-15 Formatierung (Fett/Kursiv/Unterstrichen) für die Beschreibung als schwebende Leiste, die nur über markiertem Text erscheint (statt fester Leiste); saubere <b>/<i>/<u>-Tags, bleibt im eBay-Export erhalten (Test) (index.html, app.js, style.css, Tests).
- [x] 2026-06-15 Preistabelle übersichtlicher: Spalten Angebot · Quelle · Preis (rechtsbündig, fett), aufsteigend nach Preis sortiert, lange Titel auf eine Zeile gekürzt (… + Tooltip), Zebra-Streifen, Anzahl im Hinweis (index.html, app.js, style.css).
