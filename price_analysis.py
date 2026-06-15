# price_analysis.py
"""Schätzt per Websuche eine Preisempfehlung (Spanne + Vergleichsangebote) für ein Buch."""
from pydantic import BaseModel
from web_ai import complete_json

PRICE_PROMPT = (
    "Du recherchierst den ungefähren Marktwert eines gebrauchten bzw. antiquarischen "
    "Buches für eine eBay-Verkaufsanzeige. Suche im Netz nach vergleichbaren Angeboten – "
    "bevorzugt ZVAB, Booklooker und AbeBooks (aktuelle Angebote) sowie eBay verkaufte "
    "Artikel, soweit auffindbar. Sei ehrlich: Wenn du nur wenig findest, schreibe das in "
    "das Feld note und gib eine vorsichtige Spanne. "
    "Antworte AUSSCHLIESSLICH mit einem JSON-Objekt (sonst kein Text) mit genau diesen "
    "Schlüsseln: price_low, price_high, currency, comparables, note. "
    "price_low und price_high sind Eurobeträge als Text (z. B. \"8.00\"). currency ist "
    "\"EUR\". comparables ist eine Liste von höchstens 6 Objekten "
    "{\"title\": ..., \"price\": ..., \"url\": ..., \"source\": ...}. "
    "note ist ein kurzer deutscher Hinweis zur Datenlage."
)

class Comparable(BaseModel):
    title: str = ""
    price: str = ""
    url: str = ""
    source: str = ""

class PriceAnalysis(BaseModel):
    price_low: str = ""
    price_high: str = ""
    currency: str = "EUR"
    comparables: list[Comparable] = []
    note: str = ""

def analyze_price(*, api_key: str, model: str, author: str, book_title: str,
                  title: str, language: str, publication_year: str,
                  publisher: str, book_format: str) -> PriceAnalysis:
    summary = (
        f"Buch: {author} – {book_title}. Sprache: {language}. "
        f"Verlag: {publisher}. Erscheinungsjahr: {publication_year}. "
        f"Format: {book_format}. eBay-Titel der Anzeige: {title}."
    )
    content = [{"type": "text", "text": PRICE_PROMPT + "\n\n" + summary}]
    data = complete_json(api_key=api_key, model=model, content=content)
    return PriceAnalysis(**data)
