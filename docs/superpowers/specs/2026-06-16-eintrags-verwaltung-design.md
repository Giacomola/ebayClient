# Eintrags-Verwaltung — Design

**Datum:** 2026-06-16
**Status:** freigegeben (Weg A)

## Ziel

Eine übersichtliche Verwaltung direkt auf der Seite, in der der Nutzer alle
Einträge (Fälle in Arbeit **und** fertige Anzeigen) bequem verwalten kann:
löschen, zurückhalten (speichern, aber nicht hochladen), freigeben,
archivieren und wiederherstellen.

**Feste Sicherheitsregel:** Nur Einträge im Status `in_csv` (freigegeben)
stehen in der Upload-CSV. `zurückgehalten` und `archiviert` werden **niemals**
hochgeladen.

## Datenmodell

Jeder Eintrag ist ein „Fall" (JSON in `cases/`, voller Entwurf mit Feldern +
Fotos) mit einem Status:

| Status            | Bedeutung                                  | In CSV? |
|-------------------|--------------------------------------------|---------|
| `offen`           | in Arbeit, noch nicht fertig               | nein    |
| `zurückgehalten`  | fertig & gespeichert, aber zurückgehalten  | nein    |
| `in_csv`          | freigegeben (in der Upload-CSV)            | **ja**  |
| `archiviert`      | weggeräumt, ausgeblendet                   | nein    |

(`offen` und `in_csv` existieren bereits; `zurückgehalten` und `archiviert`
kommen neu hinzu.)

## Aktionen

| Aktion             | Aus Status        | Wirkung                                                           |
|--------------------|-------------------|------------------------------------------------------------------|
| Bearbeiten         | alle (außer arch.) | Fall im Editor öffnen (vorhanden)                                |
| Zurückhalten       | offen (Entwurf)   | aktuellen Entwurf als `zurückgehalten` speichern, Fläche leeren  |
| Freigeben          | zurückgehalten    | Fall-Daten in CSV schreiben, Status → `in_csv`                   |
| Zurückziehen       | in_csv            | CSV-Zeile entfernen, Status → `zurückgehalten`                   |
| Archivieren        | offen/zurückg./in_csv | Status → `archiviert`; war `in_csv`: CSV-Zeile entfernen     |
| Wiederherstellen   | archiviert        | Status → `zurückgehalten` (nicht automatisch hochgeladen)        |
| Löschen            | alle              | Fall entfernen; war `in_csv`: auch CSV-Zeile entfernen (Rückfrage)|

## Umsetzung (kleine Schritte)

### Schritt 1 — Datenmodell + CSV-Zeile entfernen
- `cases.py`: `set_case_status(case_id, status, cases_dir)`; Status
  `zurückgehalten`/`archiviert` zugelassen. `list_cases` filtert schon nach Status.
- `ebay_csv.py`: `remove_listing(folder, author, book_title, filename)` — entfernt
  die Zeile mit passendem Autor+Buchtitel-Schlüssel (`_row_key`). Gibt zurück, ob
  etwas entfernt wurde.
- Tests für beide.

### Schritt 2 — Routen (`app.py`)
- `POST /api/cases/<id>/freigeben`
- `POST /api/cases/<id>/zurueckziehen`
- `POST /api/cases/<id>/archivieren`
- `POST /api/cases/<id>/wiederherstellen`
- `DELETE /api/cases/<id>` (vorhanden) um CSV-Entfernen bei `in_csv` ergänzen
- `POST /api/draft/zurueckhalten` — aktuellen Entwurf als `zurückgehalten` parken
- `/api/overview` um die neuen Status-Gruppen erweitern
- Tests je Route.

### Schritt 3 — Oberfläche
- Das vorhandene „Übersicht"-Fenster zur Verwaltung ausbauen: vier aufklappbare
  Abschnitte (🛠️ In Arbeit · ⏸️ Zurückgehalten · ✅ Freigegeben · 🗄️ Archiviert),
  je Zeile farbiges Status-Abzeichen und nur die passenden Knöpfe.
- Löschen mit Sicherheitsabfrage; Rückmeldung über die bestehenden Banner.
- `node --check static/app.js`.

## Tests / Abnahme
- `.venv/bin/python -m pytest -q` grün.
- `node --check static/app.js` ok.
- Manuelle Sichtprüfung der vier Abschnitte und je einer Aktion.
