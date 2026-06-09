import io
from unittest.mock import patch
from app import create_app
from ai_client import BookFields

def _client(tmp_path):
    app = create_app(config_path=str(tmp_path / "config.json"))
    app.config.update(TESTING=True)
    return app.test_client()

def test_settings_speichern_und_lesen(tmp_path):
    c = _client(tmp_path)
    r = c.post("/api/settings", json={"anthropic_api_key": "sk-x", "model": "claude-opus-4-8"})
    assert r.status_code == 200
    r2 = c.get("/api/settings")
    assert r2.get_json()["model"] == "claude-opus-4-8"

def test_generate_ohne_schluessel_gibt_fehler(tmp_path):
    c = _client(tmp_path)
    data = {"images": (io.BytesIO(b"\xff\xd8jpeg"), "1.jpg")}
    r = c.post("/api/generate", data=data, content_type="multipart/form-data")
    assert r.status_code == 400
    assert "Schlüssel" in r.get_json()["error"]

def test_generate_ruft_ai_client(tmp_path):
    c = _client(tmp_path)
    c.post("/api/settings", json={"anthropic_api_key": "sk-x"})
    fake = BookFields(title="T", author="A", book_title="B", language="Deutsch",
                      description="D")
    with patch("app.analyze_book", return_value=fake) as m:
        data = {"images": (io.BytesIO(b"\xff\xd8jpeg"), "1.jpg")}
        r = c.post("/api/generate", data=data, content_type="multipart/form-data")
    assert r.status_code == 200
    assert r.get_json()["author"] == "A"
    assert m.called
