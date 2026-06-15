# derive_instructions.py
"""Leitet aus einer Beispiel-Beschreibung zwei Anweisungstexte ab: die allgemeinen
Schreibregeln und die Beschreibungs-Anweisung. So kann der Nutzer EIN gutes Beispiel
vorgeben und daraus die Anweisungen erzeugen lassen, statt sie selbst zu formulieren.

Bewusst OHNE Websuche (use_search=False): schnell und unabhängig vom Recherche-Tempo."""
from pydantic import BaseModel, field_validator
from web_ai import complete_json

DERIVE_PROMPT = (
    "Du bekommst unten eine Beispiel-Beschreibung für eine eBay-Buchanzeige. Leite daraus "
    "zwei Anweisungstexte ab, die einer KI sagen, wie sie KÜNFTIGE Buchbeschreibungen im "
    "selben Stil und Aufbau schreiben soll. Übernimm NICHT die konkreten Inhalte des "
    "Beispiels (Autor, Titel, Verlag, Jahr usw.), sondern ausschließlich Stil, Tonfall, "
    "Satzbau, Reihenfolge der Absätze und Formatierung (z. B. HTML-Tags, keine Semikolons). "
    "Antworte AUSSCHLIESSLICH mit einem JSON-Objekt (sonst kein Text) mit genau diesen "
    "Schlüsseln: prompt_general, description. "
    "prompt_general = allgemeine Schreibregeln (Sprache, Tonfall, Formatierungsvorgaben). "
    "description = konkrete Anweisung für das Feld Beschreibung, die den Aufbau des "
    "Beispiels reproduziert: welche Absätze in welcher Reihenfolge, was in jeden Absatz "
    "gehört, welche Formatierung. Schreibe beide Texte auf Deutsch und als Anweisung an die "
    "KI (nicht als fertige Beschreibung)."
)


def _to_text(value):
    """null -> Leerstring, Zahl -> Text (robust gegen unerwartete KI-Typen)."""
    if value is None:
        return ""
    return value if isinstance(value, str) else str(value)


class DerivedInstructions(BaseModel):
    prompt_general: str = ""
    description: str = ""

    _texte = field_validator("prompt_general", "description", mode="before")(_to_text)


def derive_from_example(example: str, *, api_key: str | None = None, model: str,
                        backend: str = "api_key") -> DerivedInstructions:
    content = [{"type": "text",
                "text": DERIVE_PROMPT + "\n\nBeispiel-Beschreibung:\n" + example}]
    data = complete_json(api_key=api_key, model=model, content=content,
                         use_search=False, backend=backend)
    return DerivedInstructions(**data)
