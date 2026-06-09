from unittest.mock import patch, MagicMock
from ai_client import analyze_book, BookFields, _media_type

def test_media_type_erkennung():
    assert _media_type(b"\x89PNG\r\n") == "image/png"
    assert _media_type(b"\xff\xd8\xff") == "image/jpeg"

def test_analyze_book_gibt_bookfields():
    parsed = BookFields(title="Der Hobbit", author="J.R.R. Tolkien",
                        book_title="Der Hobbit", language="Deutsch",
                        description="Gut erhalten.")
    fake_resp = MagicMock()
    fake_resp.parsed_output = parsed
    fake_client = MagicMock()
    fake_client.messages.parse.return_value = fake_resp
    with patch("ai_client.anthropic.Anthropic", return_value=fake_client):
        result = analyze_book([b"\xff\xd8jpeg"], api_key="sk", model="claude-sonnet-4-6",
                              prompt="P")
    assert isinstance(result, BookFields)
    assert result.author == "J.R.R. Tolkien"
    assert fake_client.messages.parse.call_args.kwargs["model"] == "claude-sonnet-4-6"
