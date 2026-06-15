"""Speichert den aktuellen Arbeitsstand (Entwurf) zwischen den Sitzungen.

Ein Entwurf besteht aus den Textfeldern, den Fotos (als Base64) und der Info,
ob die Ergebnis-Ansicht sichtbar war. Alles liegt in einer einzigen JSON-Datei
neben der config.json. Bewusst einfach gehalten und robust gegen eine kaputte
Datei (dann wird ein leerer Entwurf zurückgegeben)."""
import json
import os

# images_rev zählt nur bei Foto-Änderungen hoch. So erkennt die Computerseite,
# wenn vom Handy ein Foto dazukam, ohne bei jeder Textänderung neu zu laden.
# completed = True, sobald der Fall in die eBay-Sammeldatei übernommen wurde
# („abgeschlossen"); ein offener Fall wird beim Neubeginn automatisch geparkt.
EMPTY = {"fields": {}, "images": [], "result_visible": False,
         "images_rev": 0, "completed": False}

def load_draft(path: str = "draft.json") -> dict:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
        except (json.JSONDecodeError, OSError):
            return dict(EMPTY)  # kaputte/halbe Datei nicht das Programm stören lassen
        merged = dict(EMPTY)
        merged.update(loaded)
        return merged
    return dict(EMPTY)

def save_draft(draft: dict, path: str = "draft.json") -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(draft, f, ensure_ascii=False)

def update_fields(fields: dict, result_visible: bool, path: str = "draft.json") -> dict:
    """Speichert nur die Textfelder; vorhandene Fotos bleiben erhalten."""
    draft = load_draft(path)
    draft["fields"] = fields
    draft["result_visible"] = result_visible
    save_draft(draft, path)
    return draft

def update_images(images: list, path: str = "draft.json") -> dict:
    """Speichert nur die Fotos; vorhandene Textfelder bleiben erhalten.
    Erhöht images_rev, damit andere Geräte die Änderung erkennen."""
    draft = load_draft(path)
    draft["images"] = images
    draft["images_rev"] = int(draft.get("images_rev", 0)) + 1
    save_draft(draft, path)
    return draft

def mark_completed(path: str = "draft.json") -> None:
    """Markiert den aktuellen Fall als abgeschlossen (in die Sammeldatei übernommen).
    Ein so markierter Fall wird beim Neubeginn nicht mehr geparkt."""
    draft = load_draft(path)
    draft["completed"] = True
    save_draft(draft, path)

def clear_draft(path: str = "draft.json") -> None:
    """Setzt den Entwurf zurück (für 'Neuen Fall starten')."""
    save_draft(dict(EMPTY), path)
