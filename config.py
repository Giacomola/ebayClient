import json
import os

# Allgemeine Regeln, die für die ganze KI-Analyse gelten.
DEFAULT_PROMPT_GENERAL = (
    "Du bist ein Assistent für eBay-Buchverkäufe. Analysiere die Fotos EINES Buches "
    "(Cover, Buchrücken, ggf. Impressum/Titelseite) und fülle die Anzeigenfelder aus. "
    "Schreibe auf Deutsch, sachlich und korrekt. Verwende niemals Semikolons. "
    "Halte dich an die Vorgaben für die einzelnen Felder unten."
)

# Reihenfolge, Beschriftung und Standard-Anweisung je Feld, das die KI füllt.
# (key, deutsche Beschriftung für die Oberfläche, Standard-Anweisung an die KI)
PROMPT_FIELDS = [
    ("title", "Titel",
     "Verkaufsstarker eBay-Anzeigentitel, höchstens 80 Zeichen. "
     "Empfohlene Struktur: Buchtitel – Autor."),
    ("author", "Autor",
     "Vollständige(r) Name(n) des Autors oder der Autoren."),
    ("book_title", "Buchtitel",
     "Reiner Buchtitel ohne Zusätze."),
    ("language", "Sprache",
     "Sprache des Buches, zum Beispiel Deutsch."),
    ("description", "Beschreibung",
     "Kurze, ehrliche Beschreibung des Artikels und des Autors, 2 bis 4 Sätze."),
    ("publisher", "Verlag",
     "Verlag, nur wenn sicher erkennbar, sonst leer lassen."),
    ("publication_year", "Erscheinungsjahr",
     "Erscheinungsjahr (vierstellig), nur wenn sicher erkennbar, sonst leer lassen."),
    ("book_format", "Format",
     "Einband oder Format, zum Beispiel Taschenbuch oder Gebunden, "
     "nur wenn sicher erkennbar."),
]

# Praktische Hilfs-Strukturen, abgeleitet aus PROMPT_FIELDS.
DEFAULT_FIELD_PROMPTS = {key: instr for key, _label, instr in PROMPT_FIELDS}
FIELD_LABELS = {key: label for key, label, _instr in PROMPT_FIELDS}

DEFAULTS = {
    "anthropic_api_key": "",
    "imgbb_api_key": "",
    "model": "claude-sonnet-4-6",
    "location": "Berlin",
    "shipping_service": "DE_DHLPaket",
    "shipping_cost": "5.49",
    "dispatch_time_max": "3",
    "prompt_general": DEFAULT_PROMPT_GENERAL,
    "prompt_fields": dict(DEFAULT_FIELD_PROMPTS),
}

def load_settings(path: str = "config.json") -> dict:
    settings = dict(DEFAULTS)
    settings["prompt_fields"] = dict(DEFAULT_FIELD_PROMPTS)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        # Alten Einzel-Prompt nicht mehr verwenden (sauber migrieren).
        loaded.pop("prompt", None)
        # Feld-Anweisungen mit den Standardwerten zusammenführen, damit
        # fehlende Felder immer eine sinnvolle Vorgabe haben.
        loaded_fields = loaded.pop("prompt_fields", None)
        settings.update(loaded)
        if isinstance(loaded_fields, dict):
            settings["prompt_fields"].update(loaded_fields)
    return settings

def save_settings(settings: dict, path: str = "config.json") -> None:
    merged = dict(DEFAULTS)
    merged["prompt_fields"] = dict(DEFAULT_FIELD_PROMPTS)
    incoming_fields = settings.get("prompt_fields")
    merged.update(settings)
    if isinstance(incoming_fields, dict):
        fields = dict(DEFAULT_FIELD_PROMPTS)
        fields.update(incoming_fields)
        merged["prompt_fields"] = fields
    with open(path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

def build_system_prompt(settings: dict) -> str:
    """Setzt aus allgemeinen Regeln und den Feld-Anweisungen einen KI-Prompt zusammen."""
    general = settings.get("prompt_general", DEFAULT_PROMPT_GENERAL)
    fields = settings.get("prompt_fields", DEFAULT_FIELD_PROMPTS)
    lines = [general, "", "Vorgaben für die einzelnen Felder:"]
    for key, label, _default in PROMPT_FIELDS:
        instr = fields.get(key, DEFAULT_FIELD_PROMPTS[key])
        lines.append(f"- {key} ({label}): {instr}")
    return "\n".join(lines)
