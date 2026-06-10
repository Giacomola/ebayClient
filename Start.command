#!/bin/bash
# Doppelklick-Start für den Buch-Anzeigen-Helfer.
# Richtet beim ersten Mal alles selbst ein und öffnet danach den Browser.

# In den Ordner wechseln, in dem diese Datei liegt (egal von wo gestartet).
cd "$(dirname "$0")" || exit 1

echo "Buch-Anzeigen-Helfer wird gestartet ..."

# Beim ersten Start: virtuelle Umgebung anlegen und Pakete installieren.
if [ ! -d ".venv" ]; then
  echo "Erste Einrichtung – das dauert einmalig ein bis zwei Minuten ..."
  python3 -m venv .venv || { echo "Python 3 fehlt. Bitte zuerst Python installieren."; read -r; exit 1; }
  ./.venv/bin/pip install --quiet --upgrade pip
  ./.venv/bin/pip install --quiet -r requirements.txt || { echo "Installation fehlgeschlagen."; read -r; exit 1; }
fi

# App starten (öffnet selbst den Browser auf http://127.0.0.1:5050).
echo "Fertig. Der Browser öffnet sich gleich. Dieses Fenster bitte offen lassen."
echo "Zum Beenden dieses Fenster schließen."
./.venv/bin/python app.py
