import json
import os

DEFAULT_PROMPT = (
    "Du bist ein Assistent für eBay-Buchverkäufe. Analysiere die Fotos EINES Buches "
    "(Cover, Buchrücken, ggf. Impressum/Titelseite) und liefere die Felder für die "
    "Anzeige. Schreibe auf Deutsch, sachlich und korrekt. Der Titel (title) ist ein "
    "verkaufsstarker eBay-Anzeigentitel mit höchstens 80 Zeichen ohne Semikolons. "
    "book_title ist der reine Buchtitel, author der/die Autor(en), language die Sprache "
    "des Buches (z. B. Deutsch). description ist eine kurze, ehrliche Beschreibung des "
    "Artikels und des Autors (2-4 Sätze, keine Semikolons). publisher, publication_year "
    "und book_format nur ausfüllen, wenn sicher erkennbar, sonst leer lassen."
)

DEFAULTS = {
    "anthropic_api_key": "",
    "imgbb_api_key": "",
    "model": "claude-sonnet-4-6",
    "location": "Berlin",
    "shipping_service": "DE_DHLPaket",
    "shipping_cost": "5.49",
    "dispatch_time_max": "3",
    "prompt": DEFAULT_PROMPT,
}

def load_settings(path: str = "config.json") -> dict:
    settings = dict(DEFAULTS)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            settings.update(json.load(f))
    return settings

def save_settings(settings: dict, path: str = "config.json") -> None:
    merged = dict(DEFAULTS)
    merged.update(settings)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
