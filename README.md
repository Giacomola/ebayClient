# Buch-Anzeigen-Helfer (Etappe 1)

Erzeugt aus Buchfotos per Claude einen eBay-Anzeigentext und eine fertige
eBay-File-Exchange-CSV (Fotos über imgbb gehostet).

## Start (einfach, Mac)
Auf **`Start.command`** doppelklicken. Beim ersten Mal richtet sich alles selbst
ein (ein bis zwei Minuten), danach öffnet sich der Browser auf
http://127.0.0.1:5000. Das Terminal-Fenster offen lassen; zum Beenden schließen.

> Hinweis: Beim allerersten Doppelklick warnt macOS evtl. („nicht geprüfter
> Entwickler"). Dann einmal Rechtsklick auf `Start.command` → „Öffnen" → „Öffnen".

## Start (Entwicklung, Mac/Linux)
1. `python3 -m venv .venv && . .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `python app.py` (öffnet den Browser auf http://127.0.0.1:5000)
4. Oben „Einstellungen" → Anthropic- und imgbb-Schlüssel eintragen.

## Ablauf
Fotos eines Buches reinziehen → „Anzeige erstellen" → Felder prüfen/bearbeiten,
Preis und Zustand setzen → „eBay-Datei speichern" → die CSV im eBay-CSV-Manager hochladen.

## Tests
`pytest -q`
