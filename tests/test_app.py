import io
from unittest.mock import patch
from app import create_app
from ai_client import BookFields
from price_analysis import PriceAnalysis

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

def test_open_anweisungen_oeffnet_datei(tmp_path):
    c = _client(tmp_path)  # create_app legt tmp/anweisungen.txt an
    with patch("app.subprocess.run") as m:
        r = c.post("/api/open-anweisungen")
    assert r.status_code == 200
    assert m.called
    assert m.call_args.args[0][-1].endswith("anweisungen.txt")

def test_open_anweisungen_fehlt_gibt_404(tmp_path):
    c = _client(tmp_path)
    (tmp_path / "anweisungen.txt").unlink()
    r = c.post("/api/open-anweisungen")
    assert r.status_code == 404

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

def test_generate_liefert_web_felder(tmp_path):
    c = _client(tmp_path)
    c.post("/api/settings", json={"anthropic_api_key": "sk-x"})
    fake = BookFields(title="T", author="A", book_title="B", language="Deutsch",
                      description="D", web_sourced_fields=["publisher"],
                      sources=[{"title": "ZVAB", "url": "https://x"}])
    with patch("app.analyze_book", return_value=fake):
        data = {"images": (io.BytesIO(b"\xff\xd8jpeg"), "1.jpg")}
        r = c.post("/api/generate", data=data, content_type="multipart/form-data")
    body = r.get_json()
    assert r.status_code == 200
    assert body["web_sourced_fields"] == ["publisher"]
    assert body["sources"][0]["url"] == "https://x"

def test_price_ohne_schluessel_gibt_fehler(tmp_path):
    c = _client(tmp_path)
    r = c.post("/api/price", json={"author": "A", "book_title": "B"})
    assert r.status_code == 400
    assert "Schlüssel" in r.get_json()["error"]

def test_price_ruft_analyze_price(tmp_path):
    c = _client(tmp_path)
    c.post("/api/settings", json={"anthropic_api_key": "sk-x"})
    fake = PriceAnalysis(price_low="8.00", price_high="15.00",
                         comparables=[{"title": "X", "price": "12.00",
                                       "url": "https://y", "source": "ZVAB"}],
                         note="ok")
    with patch("app.analyze_price", return_value=fake) as m:
        r = c.post("/api/price", json={"author": "A", "book_title": "B", "title": "T",
                                       "language": "Deutsch", "publication_year": "1957",
                                       "publisher": "", "book_format": ""})
    assert r.status_code == 200
    assert r.get_json()["price_low"] == "8.00"
    assert m.called
