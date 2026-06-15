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


def save_case(draft: dict, cases_dir: str = "cases", name: str | None = None) -> str:
    """Speichert den Entwurf als neuen geparkten Fall und gibt dessen ID zurück."""
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
        "draft": {
            "fields": draft.get("fields", {}),
            "images": draft.get("images", []),
            "result_visible": draft.get("result_visible", False),
        },
    }
    with open(_case_path(cases_dir, case_id), "w", encoding="utf-8") as f:
        json.dump(record, f, ensure_ascii=False)
    return case_id


def list_cases(cases_dir: str = "cases") -> list:
    """Liefert die geparkten Fälle als Kurzinfos, neueste zuerst."""
    if not os.path.isdir(cases_dir):
        return []
    out = []
    for fn in os.listdir(cases_dir):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(cases_dir, fn), encoding="utf-8") as f:
                rec = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue  # kaputte Datei nicht die Liste sprengen lassen
        out.append({
            "id": rec.get("id") or fn[:-5],
            "name": rec.get("name") or "Unbenannter Fall",
            "photo_count": len(rec.get("draft", {}).get("images", [])),
            "saved_at": rec.get("saved_at", 0),
        })
    out.sort(key=lambda c: c["saved_at"], reverse=True)
    return out


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
