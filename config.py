import json
import os

import anweisungen

# Allgemeine Regeln, die für die ganze KI-Analyse gelten.
DEFAULT_PROMPT_GENERAL = (
    "Du bist ein Assistent für den Verkauf antiquarischer und gebrauchter Bücher auf "
    "eBay.de. Analysiere die Fotos EINES Buches (Einband, Buchrücken, Titelseite, "
    "Impressum, ggf. Inhaltsverzeichnis) und fülle die Anzeigenfelder aus. Nutze die "
    "Websuche, um die exakte Ausgabe zu bestimmen und fehlende Angaben zu ergänzen. "
    "Schreibe auf Deutsch: antiquarisch korrekt UND als ansprechender Verkaufstext, der "
    "einen möglichen Käufer überzeugt – sachlich, aber einladend, ohne Übertreibung oder "
    "erfundene Angaben. Gib bevorzugt an, was auf den Fotos sicher erkennbar ist; aus dem "
    "Netz ergänzte Angaben sind erlaubt, müssen aber belegbar sein. "
    "Verwende niemals Semikolons. Formatiere die Beschreibung als eBay-taugliches HTML: "
    "Absätze mit <p>…</p>, Zeilenumbrüche mit <br>, Hervorhebungen mit <b>…</b>; verwende "
    "KEINE echten Zeilenumbrüche (Enter-Taste), sondern ausschließlich diese HTML-Tags."
)

# Anweisung für den 80-Zeichen-Anzeigentitel.
DEFAULT_TITLE_PROMPT = (
    "eBay-Anzeigentitel, höchstens 80 Zeichen, keine Semikolons. Aufbau: "
    "[Jahr] [Autor-Nachname] [Kurztitel] [Bändezahl falls Set] [Verlag] "
    "[Einband oder Übersetzer als Keyword]. Das Erscheinungsjahr steht immer an "
    "erster Stelle. Weitere Angaben nur, soweit sie in 80 Zeichen passen."
)

# Anweisung für die HTML-Beschreibung (7 Absätze in fester Reihenfolge).
DEFAULT_DESCRIPTION_PROMPT = """Falls unten eine Muster-Vorlage steht, übernimm deren Aufbau und Formatierung GENAU.
Jeder der folgenden sieben Punkte ist ein eigener Absatz <p>…</p>, in dieser Reihenfolge:
1. <p><b>Autor</b> – <b>Buchtitel</b><br>danach eine Kurzzeile mit Verlag und Ort (bei Sets auch Bändezahl).</p>
2. <p>Bibliografische Fakten, nur Erkennbares: Auflage und Jahr, Druckart (z. B. Frakturdruck), Format, Seitenzahl, Übersetzer, ISBN.</p>
3. <p>Sichtbare physische Beschreibung: Einband, Prägungen, Rücken, Gebrauchsspuren. NUR was auf den Fotos sichtbar ist – nichts aus dem Netz, nichts erfinden. Nicht beurteilbar? Auf die Fotos verweisen.</p>
4. <p><b>Zustand:</b> ehrlich und konkret, AUSSCHLIESSLICH nach den Fotos beurteilt. Bei Sets alle Bände. Schutzumschlag, Einträge, Flecken benennen. Innenzustand nicht beurteilbar? Ausdrücklich sagen und „Die Fotos sind Teil der Beschreibung.“ ergänzen.</p>
5. <p><b>Zum Werk:</b> 2–3 Sätze, die GEZIELT DIESE Ausgabe aufwerten (Bedeutung, Sammler- oder Lesereiz) – kein generisches Allgemeinwissen. Dieser Teil darf aus den Quellen stammen (bevorzugt ZVAB).</p>
6. <p>Schlagworte: 5–8 Stück, mit · getrennt.</p>
7. <p>Rechtshinweis. Privat: „Privatverkauf, keine Garantie oder Rücknahme – bitte vor dem Kauf Fragen stellen.“</p>
Formatierung: <b> nur für die Autor-/Titel-Zeile und die Marken „Zustand:“ und „Zum Werk:“. Keine Semikolons, kein Markdown, keine echten Zeilenumbrüche – ausschließlich diese HTML-Tags."""

# Reihenfolge, Beschriftung und Standard-Anweisung je Feld, das die KI füllt.
# (key, deutsche Beschriftung für die Oberfläche, Standard-Anweisung an die KI)
PROMPT_FIELDS = [
    ("title", "Titel", DEFAULT_TITLE_PROMPT),
    ("author", "Autor",
     "Verfasser mit vollständigem Namen. Wenn üblich auch die originale oder lateinische "
     "Namensform, zum Beispiel Publius Ovidius Naso (Ovid). Nur wenn sicher erkennbar."),
    ("book_title", "Buchtitel",
     "Reiner Buchtitel. Falls vorhanden mit Herausgeber, zum Beispiel "
     "Metamorphoses, Gottlieb Erdmann Gierig. Nur wenn sicher erkennbar."),
    ("language", "Sprache",
     "Sprache des Buchinhalts, zum Beispiel Deutsch oder Latein. Nur wenn sicher erkennbar."),
    ("description", "Beschreibung", DEFAULT_DESCRIPTION_PROMPT),
    ("publisher", "Verlag",
     "Verlag, nur wenn sicher erkennbar, sonst leer lassen (kein Platzhalter)."),
    ("publication_year", "Erscheinungsjahr",
     "Erscheinungsjahr vierstellig, nur wenn sicher erkennbar, sonst leer lassen "
     "(kein Platzhalter). Wird im Titel an erster Stelle verwendet."),
    ("book_format", "Format",
     "Einband und Größe/Format, nur soweit sicher ersichtlich, zum Beispiel Halbleder, "
     "Großoktav. Größe als antiquarisches Format (Oktav, Großoktav usw.) oder in cm. "
     "Sonst leer lassen (kein Platzhalter)."),
]

# Praktische Hilfs-Strukturen, abgeleitet aus PROMPT_FIELDS.
DEFAULT_FIELD_PROMPTS = {key: instr for key, _label, instr in PROMPT_FIELDS}
FIELD_LABELS = {key: label for key, label, _instr in PROMPT_FIELDS}
# (key, label)-Paare in Anzeige-Reihenfolge – Überschriften für anweisungen.txt.
_FIELD_LABELS = [(key, label) for key, label, _instr in PROMPT_FIELDS]

# Auswählbare Recherche-Quellen (key, Anzeigename, Domain). Reihenfolge in der
# gespeicherten Liste = Priorität. Der Platzhalter {PRIMAERQUELLEN} in den
# Allgemeinen Regeln wird durch den daraus gebauten Satz ersetzt.
SOURCE_CATALOG = [
    ("zvab", "ZVAB", "zvab.com"),
    ("dnb", "DNB", "portal.dnb.de"),
    ("ddb", "DDB", "deutsche-digitale-bibliothek.de"),
    ("abebooks", "AbeBooks", "abebooks.de"),
    ("booklooker", "Booklooker", "booklooker.de"),
    ("wikipedia", "Wikipedia", "wikipedia.org"),
]
_SOURCE_BY_KEY = {key: (label, domain) for key, label, domain in SOURCE_CATALOG}
DEFAULT_PRIMARY_SOURCES = ["zvab", "dnb", "ddb"]
PRIMARY_SOURCES_PLACEHOLDER = "{PRIMAERQUELLEN}"

def _clean_sources(value):
    """Behält nur bekannte Quellen-Schlüssel, in gegebener Reihenfolge, ohne Dubletten."""
    if not isinstance(value, list):
        return list(DEFAULT_PRIMARY_SOURCES)
    seen, out = set(), []
    for key in value:
        if key in _SOURCE_BY_KEY and key not in seen:
            seen.add(key)
            out.append(key)
    return out

def primary_sources_sentence(settings: dict) -> str:
    """Baut aus den gewählten Primärquellen den Recherche-Hinweis für den Prompt."""
    keys = _clean_sources(settings.get("primary_sources"))
    if not keys:
        return ("Nutze für Fakten zuverlässige Buch- und Bibliothekskataloge. "
                "Niemals raten oder erfinden.")
    parts = [f"{_SOURCE_BY_KEY[k][0]} ({_SOURCE_BY_KEY[k][1]})" for k in keys]
    liste = parts[0] if len(parts) == 1 else ", dann ".join(parts)
    return (
        "Nutze als Primärquellen in dieser Reihenfolge: " + liste + ". "
        "Andere Quellen nur heranziehen, wenn diese nichts Passendes liefern. "
        "Übernimm aus diesen Quellen nur Werk- und Ausgabe-Angaben, NICHT den Zustand "
        "(der Zustand stammt ausschließlich aus den Fotos dieses Exemplars). "
        "Fremde Beschreibungstexte nicht wörtlich kopieren, sondern in eigenen Worten "
        "zusammenfassen. Niemals raten oder erfinden."
    )

DEFAULTS = {
    # Woher die Rechenleistung kommt: "api_key" = Anthropic-API (pro Nutzung bezahlt,
    # Standard), "abo" = Claude-Abo über die Claude-Code-CLI (Verbrauch geht aufs
    # Monatsguthaben, kein API-Schlüssel nötig).
    "ki_backend": "api_key",
    "anthropic_api_key": "",
    "imgbb_api_key": "",
    # Getrennt wählbar: starkes Modell für die Texte, schnelleres für die
    # Preissuche (der Preis ist nur eine Empfehlung). "model" bleibt als
    # Alt-Schlüssel erhalten, wird aber nicht mehr verwendet.
    "model": "claude-opus-4-8",
    "model_text": "claude-opus-4-8",
    "model_price": "claude-sonnet-4-6",
    "location": "Berlin",
    "shipping_service": "DE_DHLPaket",
    "shipping_cost": "5.49",
    "dispatch_time_max": "3",
    "save_folder": "",
    # Recherche-Quellen in Prioritätsreihenfolge (siehe SOURCE_CATALOG).
    "primary_sources": list(DEFAULT_PRIMARY_SOURCES),
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
    # Die Anweisungen leben in anweisungen.txt (Quelle der Wahrheit). Ist die Datei
    # vorhanden, überschreibt sie die Prompt-Werte. Fehlende Abschnitte behalten ihren
    # bisherigen Wert (die Datei kann also nichts versehentlich leeren).
    parsed = anweisungen.load(path, _FIELD_LABELS)
    if parsed:
        if "prompt_general" in parsed:
            settings["prompt_general"] = parsed["prompt_general"]
        if "prompt_examples" in parsed:
            settings["prompt_examples"] = parsed["prompt_examples"]
        settings["prompt_fields"].update(parsed.get("prompt_fields", {}))
    settings["primary_sources"] = _clean_sources(settings.get("primary_sources"))
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
    merged["primary_sources"] = _clean_sources(merged.get("primary_sources"))
    # Anweisungen in die .txt schreiben (Quelle der Wahrheit) …
    anweisungen.save(merged.get("prompt_general", ""), merged["prompt_fields"],
                     merged.get("prompt_examples", ""), _FIELD_LABELS, path)
    # … und die config.json OHNE die Prompt-Schlüssel speichern (liegen jetzt in der .txt).
    for key in ("prompt_general", "prompt_fields", "prompt_examples"):
        merged.pop(key, None)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

def ensure_anweisungen(path: str = "config.json") -> None:
    """Legt anweisungen.txt einmalig aus den aktuell wirksamen Anweisungen an,
    falls die Datei noch fehlt. So gibt es immer eine Datei zum Direkt-Bearbeiten."""
    s = load_settings(path)
    anweisungen.ensure(s.get("prompt_general", ""), s["prompt_fields"],
                       s.get("prompt_examples", ""), _FIELD_LABELS, path)

def build_system_prompt(settings: dict) -> str:
    """Setzt aus allgemeinen Regeln und den Feld-Anweisungen einen KI-Prompt zusammen."""
    general = settings.get("prompt_general", DEFAULT_PROMPT_GENERAL)
    # Die gewählten Primärquellen einsetzen: an den Platzhalter, sonst anhängen.
    sources = primary_sources_sentence(settings)
    if PRIMARY_SOURCES_PLACEHOLDER in general:
        general = general.replace(PRIMARY_SOURCES_PLACEHOLDER, sources)
    else:
        general = general + "\n\n" + sources
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
