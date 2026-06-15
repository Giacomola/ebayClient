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

## Datenschutz (gitignored — nicht committen)

- `config.json` — API-Schlüssel (Anthropic, imgbb)
- `draft.json` — aktueller Anzeigen-Entwurf inkl. Bilddaten
- `eBay-Test-*.csv` — Test-Exporte
- `logs/` — Daemon-Logs
