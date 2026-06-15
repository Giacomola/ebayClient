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

- [ ] Zwei Titelvorschläge ausgeben (Auswahl über anklicken)  `→ ai_client.py, app.py, index.html, app.js`
- [ ] Strukturierte antiquarische Beschreibung als Vorlage für KI-Generierung (über das „Beispiel-Beschreibung"-Feld)  `→ anweisungen.txt, config.py`

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

- [x] 2026-06-15 Fehlende Informationen nicht anzeigen: KI lässt unbekannte Pflichtangaben weg statt roten Platzhalter einzusetzen (anweisungen.txt).
- [x] 2026-06-15 DnB/DDB als bevorzugte Quelle im Recherche-Prompt verankert (anweisungen.txt).
- [x] 2026-06-15 Preis-Suchbegriff: erste 4 Wörter des Buchtitels + Jahr als empfohlene Suchanfrage (price_analysis.py).
- [x] 2026-06-15 Preisvergleich: Beispielpreise zeigen den Preis fett hervorgehoben + anklickbaren Link (app.js).
