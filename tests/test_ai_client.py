# tests/test_ai_client.py
from unittest.mock import patch
from ai_client import analyze_book, BookFields, _media_type

def test_media_type_erkennung():
    assert _media_type(b"\x89PNG\r\n") == "image/png"
    assert _media_type(b"\xff\xd8\xff") == "image/jpeg"

def test_analyze_book_validiert_und_reicht_modell_durch():
    fake = {
        "title": "1937 J.R.R. Tolkien Der Hobbit Deutsch",
        "author": "J.R.R. Tolkien", "book_title": "Der Hobbit",
        "language": "Deutsch", "description": "<p>Schönes Exemplar.</p>",
        "publisher": "Klett-Cotta", "publication_year": "1937", "book_format": "Oktav",
        "web_sourced_fields": ["publication_year", "publisher"],
        "sources": [{"title": "ZVAB", "url": "https://www.zvab.com/x"}],
    }
    with patch("ai_client.complete_json", return_value=fake) as m:
        result = analyze_book([b"\x89PNGfake"], api_key="sk",
                              model="claude-opus-4-8", prompt="P")
    assert isinstance(result, BookFields)
    assert result.author == "J.R.R. Tolkien"
    assert result.web_sourced_fields == ["publication_year", "publisher"]
    assert result.sources[0].url == "https://www.zvab.com/x"
    # Modell durchgereicht und ein Bildblock im Inhalt
    assert m.call_args.kwargs["model"] == "claude-opus-4-8"
    content = m.call_args.kwargs["content"]
    assert any(b.get("type") == "image" for b in content)
    assert any(b.get("type") == "text" for b in content)

def test_bookfields_neue_felder_haben_defaults():
    # Bestehende Aufrufe ohne die neuen Felder müssen weiter funktionieren.
    bf = BookFields(title="T", author="A", book_title="B", language="Deutsch",
                    description="D")
    assert bf.web_sourced_fields == []
    assert bf.sources == []
