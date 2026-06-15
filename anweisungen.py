"""Liest und schreibt die KI-Anweisungen als einfache `.txt`-Datei mit
`# Überschrift #`-Abschnitten.

Diese Datei ist die gemeinsame Quelle der Wahrheit: Sowohl der „Anweisungen"-Tab
in der App als auch ein normaler Texteditor bearbeiten dieselbe Datei. Dadurch
bleiben beide Seiten automatisch im Gleichschritt (Zwei-Wege-Sync), ohne dass es
eine Konfliktlogik braucht.

Aufbau der Datei (Abschnitt = Überschrift + folgender Text bis zur nächsten
Überschrift):

    # Allgemeine Regeln #
    … allgemeiner Prompt …

    # Titel #
    … Anweisung für das Titelfeld …

    … weitere Felder …

    # Beispiel-Beschreibung #
    … optionale Stil-Vorlage …

Die Überschriften der Felder sind deren deutsche Beschriftungen (z. B. „Titel",
„Beschreibung"). Erkennung ist tolerant: `# Titel #`, `#Titel#` und `# Titel#`
gelten alle.
"""
import os
import re

FILENAME = "anweisungen.txt"
GENERAL_HEADLINE = "Allgemeine Regeln"
EXAMPLES_HEADLINE = "Beispiel-Beschreibung"

# Eine Zeile, die mit # beginnt und endet, ist eine Überschrift.
_HEADLINE = re.compile(r"^\s*#\s*(.+?)\s*#\s*$")


def path_for(config_path: str) -> str:
    """Pfad der Anweisungsdatei – immer neben der config.json."""
    return os.path.join(os.path.dirname(config_path), FILENAME)


def render(general: str, fields: dict, examples: str, field_labels: list) -> str:
    """Baut den Dateitext aus den einzelnen Anweisungen.

    field_labels: Liste von (key, label) in der gewünschten Reihenfolge."""
    parts = [f"# {GENERAL_HEADLINE} #", (general or "").strip(), ""]
    for key, label in field_labels:
        parts += [f"# {label} #", (fields.get(key, "") or "").strip(), ""]
    parts += [f"# {EXAMPLES_HEADLINE} #", (examples or "").strip()]
    return "\n".join(parts).rstrip() + "\n"


def parse(text: str, field_labels: list) -> dict:
    """Zerlegt den Dateitext in seine Abschnitte.

    Gibt ein dict mit nur den tatsächlich vorhandenen Schlüsseln zurück:
    `prompt_general`, `prompt_examples` und/oder `prompt_fields` (Teil-dict).
    Unbekannte Überschriften werden ignoriert; fehlende Abschnitte fehlen
    einfach (der Aufrufer behält dann seinen bisherigen Wert)."""
    label_to_key = {label: key for key, label in field_labels}
    result = {"prompt_fields": {}}
    current = None          # "general" | "examples" | ("field", key) | None
    buf: list = []

    def flush():
        if current is None:
            return
        content = "\n".join(buf).strip()
        if current == "general":
            result["prompt_general"] = content
        elif current == "examples":
            result["prompt_examples"] = content
        else:
            result["prompt_fields"][current[1]] = content

    for line in text.splitlines():
        m = _HEADLINE.match(line)
        if m:
            flush()
            buf = []
            title = m.group(1).strip()
            if title == GENERAL_HEADLINE:
                current = "general"
            elif title == EXAMPLES_HEADLINE:
                current = "examples"
            elif title in label_to_key:
                current = ("field", label_to_key[title])
            else:
                current = None      # unbekannte Überschrift -> Abschnitt verwerfen
            continue
        if current is not None:
            buf.append(line)
    flush()

    if not result["prompt_fields"]:
        result.pop("prompt_fields")
    return result


def load(config_path: str, field_labels: list):
    """Liest die Anweisungsdatei (falls vorhanden) und gibt das Parse-Ergebnis
    zurück, sonst None. Schreibt NICHTS (reine Lesefunktion)."""
    p = path_for(config_path)
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return parse(f.read(), field_labels)


def save(general: str, fields: dict, examples: str, field_labels: list,
         config_path: str) -> None:
    """Schreibt die Anweisungsdatei neben der config.json."""
    with open(path_for(config_path), "w", encoding="utf-8") as f:
        f.write(render(general, fields, examples, field_labels))


def ensure(general: str, fields: dict, examples: str, field_labels: list,
           config_path: str) -> None:
    """Legt die Datei einmalig an, falls sie noch fehlt (Migration aus den
    aktuell wirksamen Anweisungen) – bestehende Dateien bleiben unangetastet."""
    if not os.path.exists(path_for(config_path)):
        save(general, fields, examples, field_labels, config_path)
