import json
import os

# Allgemeine Regeln, die für die ganze KI-Analyse gelten.
DEFAULT_PROMPT_GENERAL = (
    "Du bist ein Assistent für den Verkauf antiquarischer und gebrauchter Bücher auf "
    "eBay.de. Analysiere die Fotos EINES Buches (Einband, Buchrücken, Titelseite, "
    "Impressum, ggf. Inhaltsverzeichnis) und fülle die Anzeigenfelder aus. Schreibe auf "
    "Deutsch, sachlich und korrekt im Stil einer antiquarischen Beschreibung. Gib nur an, "
    "was auf den Fotos sicher erkennbar ist; rate nichts dazu und lass Unsicheres weg. "
    "Verwende niemals Semikolons. Formatiere die Beschreibung als eBay-taugliches HTML: "
    "Absätze mit <p>…</p>, Zeilenumbrüche mit <br>, Hervorhebungen mit <b>…</b>; verwende "
    "KEINE echten Zeilenumbrüche (Enter-Taste), sondern ausschließlich diese HTML-Tags."
)

# Reihenfolge, Beschriftung und Standard-Anweisung je Feld, das die KI füllt.
# (key, deutsche Beschriftung für die Oberfläche, Standard-Anweisung an die KI)
PROMPT_FIELDS = [
    ("title", "Titel",
     "eBay-Anzeigentitel mit höchstens 80 Zeichen. Das Erscheinungsjahr steht IMMER an "
     "erster Stelle. Danach, soweit es in 80 Zeichen passt, in dieser Reihenfolge: Autor, "
     "Buchtitel, Sprache, Verlag, Original oder Faksimile, Genre/Thema, Einband, "
     "Erscheinungsort, Format/Größe. Keine Semikolons."),
    ("author", "Autor",
     "Verfasser mit vollständigem Namen; wenn üblich auch die originale bzw. lateinische "
     "Namensform, zum Beispiel Publius Ovidius Naso (Ovid)."),
    ("book_title", "Buchtitel",
     "Reiner Buchtitel; falls vorhanden mit Herausgeber, zum Beispiel "
     "Metamorphoses, Gottlieb Erdmann Gierig."),
    ("language", "Sprache",
     "Sprache des Buchinhalts, zum Beispiel Deutsch oder Latein."),
    ("description", "Beschreibung",
     "Strukturierte antiquarische Beschreibung als Fließtext mit Absätzen (HTML: <p>, "
     "<br>, <b>) in genau dieser Reihenfolge: "
     "1. Verfasser (Verfassername in <b>fett</b>). "
     "2. Titel, danach Herausgeber. "
     "3. Erscheinungsort / Verlag / Jahr, z. B. Lipsiae (Leipzig), sumtu E. B. "
     "Schwickerti, 1807. "
     "4. Auflage und Band, z. B. Editio altera …, Tomus posterior. "
     "5. Format und Größe (Oktav, Großoktav usw. oder in cm), Seitenzahl und Einband. "
     "6. Zustandsbeschreibung unter Berücksichtigung des Einbandes. "
     "7. Inhalt des Buches sowie Angaben zum Verfasser/Autor. "
     "Nenne, falls erkennbar, ob es sich um ein Original oder ein Faksimile handelt, "
     "sowie Genre/Thema (Unterthema/Spezialthema). Ist ein Inhaltsverzeichnis sichtbar, "
     "ergänze am Ende eine kurze Verschlagwortung (Stichwörter) daraus."),
    ("publisher", "Verlag",
     "Verlag, nur wenn erkennbar, sonst leer lassen."),
    ("publication_year", "Erscheinungsjahr",
     "Erscheinungsjahr (vierstellig), nur wenn erkennbar. Wird im Titel an erster Stelle "
     "verwendet."),
    ("book_format", "Format",
     "Einband und Größe/Format, soweit ersichtlich, zum Beispiel Halbleder, Großoktav. "
     "Größe als antiquarisches Format (Oktav, Großoktav usw.) oder in cm."),
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
    "save_folder": "",
    "prompt_general": DEFAULT_PROMPT_GENERAL,
    "prompt_fields": dict(DEFAULT_FIELD_PROMPTS),
    "prompt_examples": "",   # optionale Beispiel-Beschreibung(en) als Stil-Vorlage
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
    examples = settings.get("prompt_examples", "").strip()
    if examples:
        lines += [
            "",
            "Beispiel-Beschreibung (nur als Stil- und Aufbau-Vorlage): Übernimm Tonfall, "
            "Struktur und Formatierung, aber NICHT die konkreten Angaben (Autor, Titel, "
            "Verlag, Jahr usw.). Alle Fakten stammen ausschließlich aus den Fotos des "
            "aktuellen Buches.",
            examples,
        ]
    return "\n".join(lines)
