#!/bin/bash
# Startet den INBOX-Daemon (sortiert beim Speichern automatisch in den Backlog).
# Läuft in diesem Fenster; zum Beenden Strg-C drücken oder das Fenster schließen.
cd "$(dirname "$0")"
./.venv/bin/python -c "import watchdog" >/dev/null 2>&1 \
  || ./.venv/bin/python -m pip install watchdog
exec ./.venv/bin/python tools/inbox_daemon.py
