# price_analysis.py
"""Sucht per Websuche echte Beispielpreise (Vergleichsangebote) für ein Buch.

Bewusst KEINE eigene Preisempfehlung und keine Spanne – nur die tatsächlich im Netz
gefundenen Angebote mit Quelle, damit der Verkäufer selbst entscheidet."""
from pydantic import BaseModel, field_validator
from web_ai import complete_json

def _to_text(value):
    """Macht aus null einen Leerstring und aus Zahlen Text.

    Die KI liefert für Textfelder manchmal null (nichts gefunden) oder eine Zahl
    statt eines Strings – beides würde sonst die Validierung sprengen."""
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    return value

PRICE_PROMPT = (
    "Du suchst echte Beispielpreise (Vergleichsangebote) für ein gebrauchtes bzw. "
    "antiquarisches Buch, damit der Verkäufer selbst einen Preis festlegen kann. Suche "
    "im Netz nach konkreten Angeboten desselben oder eines sehr ähnlichen Buches – "
    "bevorzugt ZVAB, Booklooker und AbeBooks (aktuelle Angebote) sowie eBay (verkaufte "
    "Artikel), soweit auffindbar. Gib KEINE eigene Preisempfehlung und KEINE Preisspanne "
    "ab – ausschließlich die tatsächlich gefundenen Beispielpreise mit Quelle. "
    "Antworte AUSSCHLIESSLICH mit einem JSON-Objekt (sonst kein Text) mit genau diesen "
    "Schlüsseln: comparables, note. comparables ist eine Liste von höchstens 8 Objekten "
    "{\"title\": ..., \"price\": ..., \"url\": ..., \"source\": ...} mit dem jeweils "
    "angezeigten Preis und einem funktionierenden Link. note ist ein kurzer, neutraler "
    "Hinweis zur Datenlage (z. B. wie viele Angebote gefunden wurden) – KEINE Preisempfehlung."
)

class Comparable(BaseModel):
    title: str = ""
    price: str = ""
    url: str = ""
    source: str = ""

    _texte = field_validator("title", "price", "url", "source",
                             mode="before")(_to_text)

class PriceAnalysis(BaseModel):
    comparables: list[Comparable] = []
    note: str = ""

    _texte = field_validator("note", mode="before")(_to_text)

def analyze_price(*, api_key: str, model: str, author: str, book_title: str,
                  title: str, language: str, publication_year: str,
                  publisher: str, book_format: str) -> PriceAnalysis:
    summary = (
        f"Buch: {author} – {book_title}. Sprache: {language}. "
        f"Verlag: {publisher}. Erscheinungsjahr: {publication_year}. "
        f"Format: {book_format}. eBay-Titel der Anzeige: {title}."
    )
    content = [{"type": "text", "text": PRICE_PROMPT + "\n\n" + summary}]
    # Die Preissuche darf etwas mehr suchen als die Textgenerierung (Standard 2),
    # damit sie Angebote von mehreren Seiten (ZVAB, Booklooker, AbeBooks, eBay)
    # zusammentragen kann. Sie läuft nur auf Knopfdruck, daher vertretbar.
    data = complete_json(api_key=api_key, model=model, content=content, max_searches=3)
    return PriceAnalysis(**data)
