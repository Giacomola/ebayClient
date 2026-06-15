"""Verwaltet geparkte Fälle (begonnen, aber noch nicht abgeschlossen).

Der aktuelle Fall lebt weiterhin in der draft.json. Wird ein neuer Fall
begonnen, obwohl der alte noch offen ist, wandert der alte als eigene
JSON-Datei in den Ordner cases/. Eine Datei enthält Name, Speicherzeitpunkt
und den kompletten Entwurf (Felder + Fotos).

Bewusst einfach gehalten und robust: kaputte Dateien werden beim Auflisten
übersprungen, und eine Fall-ID vom Browser darf nur aus harmlosen Zeichen
bestehen (Schutz gegen Pfad-Tricks wie ../config)."""
import json
import os
import re
import time

# Erlaubte Form einer Fall-ID: genau das, was save_case erzeugt.
_ID_RE = re.compile(r"^case_[0-9_]+$")


def _case_path(cases_dir: str, case_id: str) -> str:
    return os.path.join(cases_dir, case_id + ".json")


def _name_from_fields(fields: dict) -> str:
    """Bildet einen Anzeigenamen aus Autor und Buchtitel, soweit vorhanden."""
    autor = (fields.get("author") or "").strip()
    titel = (fields.get("book_title") or fields.get("title") or "").strip()
    teile = [t for t in (autor, titel) if t]
    return " – ".join(teile)


def save_case(draft: dict, cases_dir: str = "cases", name: str | None = None,
              status: str = "offen", csv_title: str = "") -> str:
    """Speichert den Entwurf als Fall und gibt dessen ID zurück.

    status="offen" = begonnen, noch nicht abgesendet (zum Wiederaufnehmen).
    status="in_csv" = bereits in der Sammeldatei; csv_title ist dann der genaue
    Titel der CSV-Zeile (zum Zuordnen beim Bearbeiten)."""
    os.makedirs(cases_dir, exist_ok=True)
    case_id = "case_%d" % int(time.time() * 1000)
    i = 0
    while os.path.exists(_case_path(cases_dir, case_id)):  # IDs eindeutig halten
        i += 1
        case_id = "case_%d_%d" % (int(time.time() * 1000), i)
    name = name or _name_from_fields(draft.get("fields", {})) or \
        ("Unbenannter Fall – " + time.strftime("%d.%m.%Y %H:%M"))
    record = {
        "id": case_id,
        "name": name,
        "saved_at": time.time(),
        "status": status,
        "csv_title": csv_title,
        "draft": {
            "fields": draft.get("fields", {}),
            "images": draft.get("images", []),
            "result_visible": draft.get("result_visible", False),
            "price_result": draft.get("price_result"),   # Preis-Ergebnis mit aufheben
        },
    }
    with open(_case_path(cases_dir, case_id), "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False)
    return case_id


def _read_record(cases_dir: str, fn: str):
    """Liest einen Fall-Datensatz; gibt None bei kaputter/fehlender Datei zurück."""
    try:
        with open(os.path.join(cases_dir, fn), encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def list_cases(cases_dir: str = "cases", status: str | None = None) -> list:
    """Liefert Fälle als Kurzinfos, neueste zuerst. status filtert (z. B. nur "offen").
    Fehlt das Status-Feld (alte Fälle), gilt der Fall als "offen"."""
    if not os.path.isdir(cases_dir):
        return []
    out = []
    for fn in os.listdir(cases_dir):
        if not fn.endswith(".json"):
            continue
        rec = _read_record(cases_dir, fn)
        if rec is None:
            continue  # kaputte Datei nicht die Liste sprengen lassen
        st = rec.get("status", "offen")
        if status is not None and st != status:
            continue
        out.append({
            "id": rec.get("id") or fn[:-5],
            "name": rec.get("name") or "Unbenannter Fall",
            "photo_count": len(rec.get("draft", {}).get("images", [])),
            "saved_at": rec.get("saved_at", 0),
            "status": st,
        })
    out.sort(key=lambda c: c["saved_at"], reverse=True)
    return out


def find_csv_case_id(csv_title: str, cases_dir: str = "cases") -> str | None:
    """ID des „in Sammeldatei"-Falls mit genau diesem CSV-Titel (oder None)."""
    if not (csv_title or "").strip() or not os.path.isdir(cases_dir):
        return None
    for fn in os.listdir(cases_dir):
        if not fn.endswith(".json"):
            continue
        rec = _read_record(cases_dir, fn)
        if rec and rec.get("status") == "in_csv" and rec.get("csv_title") == csv_title:
            return rec.get("id") or fn[:-5]
    return None


def case_status(case_id: str, cases_dir: str = "cases") -> str | None:
    """Status eines Falls ("offen"/"in_csv") oder None, wenn es ihn nicht gibt."""
    if not _ID_RE.match(case_id or ""):
        return None
    rec = _read_record(cases_dir, case_id + ".json")
    return rec.get("status", "offen") if rec else None


def delete_in_csv_cases(cases_dir: str = "cases") -> int:
    """Löscht alle „in Sammeldatei"-Fälle (z. B. beim Archivieren). Anzahl zurück."""
    if not os.path.isdir(cases_dir):
        return 0
    n = 0
    for fn in os.listdir(cases_dir):
        if not fn.endswith(".json"):
            continue
        rec = _read_record(cases_dir, fn)
        if rec and rec.get("status") == "in_csv":
            try:
                os.remove(os.path.join(cases_dir, fn))
                n += 1
            except OSError:
                pass
    return n


def load_case(case_id: str, cases_dir: str = "cases") -> dict | None:
    """Lädt den Entwurf eines geparkten Falls (oder None, wenn nicht vorhanden)."""
    if not _ID_RE.match(case_id or ""):
        return None
    path = _case_path(cases_dir, case_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            rec = json.load(f)
    except (json.JSONDecodeError, OSError):
        return None
    return rec.get("draft")


def delete_case(case_id: str, cases_dir: str = "cases") -> bool:
    """Löscht einen geparkten Fall. Gibt True zurück, wenn etwas entfernt wurde."""
    if not _ID_RE.match(case_id or ""):
        return False
    try:
        os.remove(_case_path(cases_dir, case_id))
        return True
    except OSError:
        return False
