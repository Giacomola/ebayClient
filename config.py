import json
import os

# Allgemeine Regeln, die für die ganze KI-Analyse gelten.
DEFAULT_PROMPT_GENERAL = """### eBay-Anzeige für antiquarische & gebrauchte Bücher
Erstelle aus den Fotos EINES Buches eine fertige, verkaufsstarke und rechtssichere Anzeige auf Deutsch.

## INHALT
- Nur was auf den Fotos sicher erkennbar ist. Niemals raten oder erfinden. Du hast NUR die Fotos – nicht recherchieren.
- Pflichtangaben prüfen und, wenn erkennbar, nennen: Autor, Titel (bei Sets Vollständigkeit und Einzeltitel), Übersetzer (bei fremdsprachigem Original immer prüfen), Herausgeber, Verlag und Ort, Sprache, Format/Größe, Einband und Schutzumschlag, Seitenzahl, Auflage und Jahr, ISBN, Zustand, Genre/Thema.
- Nicht erkennbare Pflichtangabe an Ort und Stelle als FARBIGEN Platzhalter einsetzen, exakt so: <span style="color:#c00">[Angabe – bitte prüfen]</span> (zum Beispiel <span style="color:#c00">[Jahr – bitte prüfen]</span>).
- Zustand ehrlich und vorsichtig formulieren (rechtlich bindend). Keine Übertreibungen wie „neuwertig“ oder „makellos“ ohne sichtbaren Beleg.

## FORM (WICHTIG – sonst zeigt eBay Fehler an)
- Formatiere AUSSCHLIESSLICH mit HTML: Absätze <p>…</p>, Zeilenumbruch <br>, fett <b>…</b>, Farbe <span style="color:#c00">…</span>.
- NIEMALS Markdown (kein **, *, #, -). NIEMALS Semikolons. KEINE echten Zeilenumbrüche – nur die HTML-Tags."""

# Anweisung für den 80-Zeichen-Anzeigentitel.
DEFAULT_TITLE_PROMPT = (
    "eBay-Anzeigentitel, höchstens 80 Zeichen, keine Semikolons. Aufbau: "
    "[Jahr] [Autor-Nachname] [Kurztitel] [Bändezahl falls Set] [Verlag] "
    "[Einband oder Übersetzer als Keyword]. Das Erscheinungsjahr steht immer an "
    "erster Stelle. Weitere Angaben nur, soweit sie in 80 Zeichen passen."
)

# Anweisung für die HTML-Beschreibung (7 Absätze in fester Reihenfolge).
DEFAULT_DESCRIPTION_PROMPT = """Beschreibung als HTML-Fließtext mit Absätzen (<p>), in dieser Reihenfolge:
1. <b>Autor</b> – <b>Titel</b>, darunter eine Kurzzeile mit Bänden, Verlag und Ort.
2. Bibliografische Fakten in EINEM Satz, nur Erkennbares: Vollständigkeit/Einzeltitel, Übersetzer, Auflage und Jahr, Format, Einband, Seitenzahl, ISBN.
3. Sichtbare physische Beschreibung: Einbandmotive, Prägungen, Rücken – nur Belegbares.
4. <b>Zustand:</b> ehrlich und konkret. Bei Sets alle Bände. Schutzumschlag, Einträge, Flecken benennen. Innenzustand nicht beurteilbar? Ausdrücklich sagen und „Die Fotos sind Teil der Beschreibung.“ ergänzen.
5. <b>Zum Werk:</b> 2–3 Sätze, die GEZIELT DIESE Ausgabe aufwerten (Bedeutung, Sammler- oder Lesereiz) – kein generisches Allgemeinwissen.
6. Schlagworte: 5–8 Stück, mit · getrennt.
7. Rechtshinweis je nach Verkäufertyp. Privat: „Privatverkauf, keine Garantie oder Rücknahme – bitte vor dem Kauf Fragen stellen.“"""

# Reihenfolge, Beschriftung und Standard-Anweisung je Feld, das die KI füllt.
# (key, deutsche Beschriftung für die Oberfläche, Standard-Anweisung an die KI)
PROMPT_FIELDS = [
    ("title", "Titel", DEFAULT_TITLE_PROMPT),
    ("author", "Autor",
     "Verfasser mit vollständigem Namen; wenn üblich auch die originale bzw. lateinische "
     "Namensform, zum Beispiel Publius Ovidius Naso (Ovid)."),
    ("book_title", "Buchtitel",
     "Reiner Buchtitel; falls vorhanden mit Herausgeber, zum Beispiel "
     "Metamorphoses, Gottlieb Erdmann Gierig."),
    ("language", "Sprache",
     "Sprache des Buchinhalts, zum Beispiel Deutsch oder Latein."),
    ("description", "Beschreibung", DEFAULT_DESCRIPTION_PROMPT),
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
