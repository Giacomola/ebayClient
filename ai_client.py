# ai_client.py
"""Schickt Buchfotos an Claude (mit Websuche) und erhält strukturierte Anzeigenfelder."""
import base64
from pydantic import BaseModel
from web_ai import complete_json

# Maschinen-Vertrag: was die KI als JSON zurückgeben muss. Wird an den (vom Nutzer
# bearbeitbaren) Prompt angehängt, damit die Felder verlässlich ankommen.
JSON_INSTRUCTIONS = (
    "\n\nNutze die Websuche, um die EXAKTE Ausgabe des Buches zu bestimmen (Auflage, "
    "Druck, Erscheinungsjahr) und fehlende Angaben zu ergänzen. Ergänze großzügig, aber "
    "nur Belegbares. Antworte AUSSCHLIESSLICH mit einem JSON-Objekt (sonst kein Text) mit "
    "genau diesen Schlüsseln: title, author, book_title, language, description, publisher, "
    "publication_year, book_format, web_sourced_fields, sources. "
    "web_sourced_fields ist eine Liste der Feldnamen, deren Inhalt aus der Websuche stammt "
    "(z. B. [\"publication_year\", \"publisher\"]). sources ist eine Liste von Objekten "
    "{\"title\": ..., \"url\": ...} mit den verwendeten Quellen (leer lassen, wenn keine "
    "Websuche nötig war)."
)

class Source(BaseModel):
    title: str = ""
    url: str = ""

class BookFields(BaseModel):
    title: str
    author: str
    book_title: str
    language: str
    description: str
    publisher: str = ""
    publication_year: str = ""
    book_format: str = ""
    web_sourced_fields: list[str] = []
    sources: list[Source] = []

def _media_type(image_bytes: bytes) -> str:
    if image_bytes[:8].startswith(b"\x89PNG"):
        return "image/png"
    return "image/jpeg"

def analyze_book(images: list[bytes], *, api_key: str, model: str, prompt: str) -> BookFields:
    content = []
    for img in images:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": _media_type(img),
                "data": base64.standard_b64encode(img).decode("ascii"),
            },
        })
    content.append({"type": "text", "text": prompt + JSON_INSTRUCTIONS})
    data = complete_json(api_key=api_key, model=model, content=content)
    return BookFields(**data)
