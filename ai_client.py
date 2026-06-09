"""Schickt Buchfotos an Claude (Vision) und erhält strukturierte Anzeigenfelder."""
import base64
import anthropic
from pydantic import BaseModel

class BookFields(BaseModel):
    title: str
    author: str
    book_title: str
    language: str
    description: str
    publisher: str = ""
    publication_year: str = ""
    book_format: str = ""

def _media_type(image_bytes: bytes) -> str:
    if image_bytes[:8].startswith(b"\x89PNG"):
        return "image/png"
    return "image/jpeg"

def analyze_book(images: list[bytes], *, api_key: str, model: str, prompt: str) -> BookFields:
    client = anthropic.Anthropic(api_key=api_key)
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
    content.append({"type": "text", "text": prompt})
    resp = client.messages.parse(
        model=model,
        max_tokens=2000,
        messages=[{"role": "user", "content": content}],
        output_format=BookFields,
    )
    return resp.parsed_output
