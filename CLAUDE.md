# Buch-Anzeigen-Helfer — Projekt-Hinweise

Flask-App (Port 5050), erzeugt aus Buchfotos per Claude einen eBay-Anzeigentext
und eine eBay-File-Exchange-CSV (Fotos über imgbb). Start per `Buch-Anzeigen-Helfer.app`
oder `Start.command`. Tests: `pytest -q`.

## Backlog-Workflow

Wünsche landen formlos in `INBOX.md` (**nur der Nutzer schreibt dort**). `BACKLOG.md`
ist die geordnete Aufgabenliste, die **Claude** pflegt — aus der Inbox in die Tabs
einsortieren, Status führen, Erledigtes abhaken. Ein optionaler Hintergrund-Daemon
(`tools/inbox_daemon.py`) sortiert beim Speichern automatisch (siehe README).

Verbindliche Kurzregeln:

- **Nur explizit benannte Dateien stagen** — immer `git add <datei> …`, NIE `git add -A`/`.`/`-a`.
- **`BACKLOG.md`: lesen → ändern → committen in EINEM Zug** (vermeidet Kollision mit dem Daemon).
  Schon fremd geändert → auf dessen Commit warten.
- **Inbox-Einträge in den passenden Tab** einsortieren als `- [ ] <Text>  `→ <datei>``;
  der `→ datei`-Tag (von Claude gesetzt) zeigt die voraussichtlich betroffene(n) Datei(en).
- **Autonom abarbeiten**, aber **unklare/schädliche/nachteilige** Punkte nach
  `##### Discussion #####` (mit `> Grund: …`) verschieben statt blind ausführen.
- **Chat-Aufträge** ebenfalls in `BACKLOG.md` festhalten (Erledigtes nach „✅ Erledigt" mit Hash).
- **Vor dem Editieren häufiger Dateien kurz Git-Stand prüfen** (`git log -5 --oneline -- <datei>`):
  `app.py`, `draft.py`, `ebay_csv.py`, `config.py`, `BACKLOG.md`.

## App-Wissen für den Frage-Chat (`chat_wissen.txt`)

`chat_wissen.txt` (neben `app.py`, in git) ist die **einzige Wissensquelle** des
eingebauten „Fragen"-Chats: Die Route `/api/chat` liest sie über `_chat_wissen()`
und ergänzt nur den aktuellen Einträge-Stand. Damit der Chat immer stimmt, gilt:

- **Bei jeder neuen oder geänderten nutzersichtbaren Funktion** (Knöpfe, Felder,
  Abläufe, Einstellungen) `chat_wissen.txt` im selben Schritt aktualisieren.
- **Nur beschreiben, was wirklich existiert** — keine erfundenen Knöpfe/Funktionen;
  die Datei weist den Chat ausdrücklich an, sich strikt an ihren Inhalt zu halten.
- Die Datei wird teils auch **zwei-Wege im Programm bearbeitet** — vor dem Ändern
  Git-Stand prüfen; ist sie schon fremd/uncommittet geändert, erst klären/abwarten
  statt zu überschreiben.

## Datenschutz (gitignored — nicht committen)

- `config.json` — API-Schlüssel (Anthropic, imgbb)
- `draft.json` — aktueller Anzeigen-Entwurf inkl. Bilddaten
- `eBay-Test-*.csv` — Test-Exporte
- `logs/` — Daemon-Logs
