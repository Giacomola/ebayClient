# Buch-Anzeigen-Helfer (Etappe 1)

Erzeugt aus Buchfotos per Claude einen eBay-Anzeigentext und eine fertige
eBay-File-Exchange-CSV (Fotos über imgbb gehostet).

## Start (einfach, Mac)
Auf **`Buch-Anzeigen-Helfer.app`** doppelklicken. Die App läuft unsichtbar im
Hintergrund (kein Terminal), der Browser öffnet sich auf http://127.0.0.1:5050.
Beim allerersten Mal richtet sich alles selbst ein (ein bis zwei Minuten).
**Beenden:** unten auf der Seite der Knopf „Programm beenden".

> Hinweis: Beim allerersten Doppelklick warnt macOS evtl. („nicht geprüfter
> Entwickler"). Dann einmal Rechtsklick auf die App → „Öffnen" → „Öffnen".
>
> Die App wird aus `launcher.applescript` erzeugt mit:
> `osacompile -o "Buch-Anzeigen-Helfer.app" launcher.applescript`
> Alternativ tut es weiterhin der Terminal-Weg über `Start.command`.

## Start (Entwicklung, Mac/Linux)
1. `python3 -m venv .venv && . .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `python app.py` (öffnet den Browser auf http://127.0.0.1:5050)
4. Oben „Einstellungen" → Anthropic- und imgbb-Schlüssel eintragen.

## Ablauf
Fotos eines Buches reinziehen → „Anzeige erstellen" → Felder prüfen/bearbeiten,
Preis und Zustand setzen → „eBay-Datei speichern" → die CSV im eBay-CSV-Manager hochladen.

## Tests
`pytest -q`
