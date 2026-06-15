# price_analysis.py
"""Sucht per Websuche echte Beispielpreise (Vergleichsangebote) für ein Buch und
leitet daraus einen realistischen Verkaufspreis ab.

Geliefert werden die gefundenen Angebote mit Quelle PLUS ein von der KI gewählter,
begründeter Preisvorschlag, der Zustand und Ausgabe berücksichtigt. Der Vorschlag
ist und bleibt nur eine Empfehlung – der Verkäufer kann ihn frei überschreiben."""
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
    "Du recherchierst echte Vergleichsangebote für ein gebrauchtes bzw. antiquarisches "
    "Buch und leitest daraus einen realistischen Verkaufspreis ab. Suche im Netz nach "
    "konkreten Angeboten desselben oder eines sehr ähnlichen Buches – bevorzugt ZVAB, "
    "Booklooker und AbeBooks (aktuelle Angebote) sowie eBay (verkaufte Artikel), soweit "
    "auffindbar. Wähle daraus einen realistischen Verkaufspreis für GENAU DIESES Exemplar "
    "und berücksichtige dabei den angegebenen Zustand und die Ausgabe (Erscheinungsjahr, "
    "Verlag, Format). Antworte AUSSCHLIESSLICH mit einem JSON-Objekt (sonst kein Text) mit "
    "genau diesen Schlüsseln: comparables, recommended_price, price_reason, note. "
    "comparables ist eine Liste von höchstens 8 Objekten {\"title\": ..., \"price\": ..., "
    "\"url\": ..., \"source\": ...} mit dem jeweils angezeigten Preis und einem "
    "funktionierenden Link. recommended_price ist eine Zahl in Euro OHNE Währungszeichen "
    "(z. B. \"12.50\") – der empfohlene Verkaufspreis. price_reason ist EIN kurzer Satz, "
    "der die Wahl begründet (Zustand, Ausgabe, Lage der Vergleichspreise). note ist ein "
    "kurzer, neutraler Hinweis zur Datenlage (z. B. wie viele Angebote gefunden wurden). "
    "Findest du zu wenige Vergleichsangebote für eine seriöse Einschätzung, lass "
    "recommended_price leer und erkläre das kurz in price_reason."
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
    recommended_price: str = ""   # von der KI empfohlener Verkaufspreis (nur Zahl)
    price_reason: str = ""        # kurze Begründung des Vorschlags
    note: str = ""

    _texte = field_validator("recommended_price", "price_reason", "note",
                             mode="before")(_to_text)

def analyze_price(*, api_key: str | None = None, model: str, author: str, book_title: str,
                  title: str, language: str, publication_year: str,
                  publisher: str, book_format: str, condition: str = "",
                  backend: str = "api_key") -> PriceAnalysis:
    summary = (
        f"Buch: {author} – {book_title}. Sprache: {language}. "
        f"Verlag: {publisher}. Erscheinungsjahr: {publication_year}. "
        f"Format: {book_format}. Zustand: {condition}. eBay-Titel der Anzeige: {title}."
    )
    # Empfohlener Suchbegriff: die ersten vier Wörter des Buchtitels plus das Jahr.
    # Das hält die Suche treffsicher und kurz (lange Volltitel liefern oft nichts).
    suchbegriff = " ".join(book_title.split()[:4])
    if publication_year.strip():
        suchbegriff = f"{suchbegriff} {publication_year.strip()}".strip()
    if suchbegriff:
        summary += (f"\n\nSuche bevorzugt mit genau diesem Suchbegriff: \"{suchbegriff}\". "
                    "Erst wenn das zu wenige Treffer liefert, leicht abwandeln.")
    content = [{"type": "text", "text": PRICE_PROMPT + "\n\n" + summary}]
    # Die Preissuche darf etwas mehr suchen als die Textgenerierung (Standard 2),
    # damit sie Angebote von mehreren Seiten (ZVAB, Booklooker, AbeBooks, eBay)
    # zusammentragen kann. Sie läuft nur auf Knopfdruck, daher vertretbar.
    data = complete_json(api_key=api_key, model=model, content=content, max_searches=3,
                         backend=backend)
    return PriceAnalysis(**data)
