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

def test_primary_sources_persistiert(tmp_path):
    c = _client(tmp_path)
    r = c.post("/api/settings", json={"primary_sources": ["dnb", "zvab"]})
    assert r.status_code == 200
    assert c.get("/api/settings").get_json()["primary_sources"] == ["dnb", "zvab"]

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

def test_open_csv_oeffnet_datei(tmp_path):
    from ebay_csv import DEFAULT_FILENAME
    c = _client(tmp_path)
    folder = tmp_path / "ebay"
    folder.mkdir()
    (folder / DEFAULT_FILENAME).write_text("x", encoding="utf-8")
    c.post("/api/settings", json={"save_folder": str(folder)})
    with patch("app.subprocess.run") as m:
        r = c.post("/api/open-csv")
    assert r.status_code == 200
    assert m.called
    assert m.call_args.args[0][-1].endswith(DEFAULT_FILENAME)

def test_open_csv_ohne_ordner_gibt_fehler(tmp_path):
    c = _client(tmp_path)
    r = c.post("/api/open-csv")
    assert r.status_code == 400

def test_open_csv_ohne_datei_gibt_404(tmp_path):
    c = _client(tmp_path)
    folder = tmp_path / "leer"
    folder.mkdir()
    c.post("/api/settings", json={"save_folder": str(folder)})
    r = c.post("/api/open-csv")
    assert r.status_code == 404

def test_listings_liefert_eintraege(tmp_path):
    from ebay_csv import append_listing
    c = _client(tmp_path)
    folder = tmp_path / "out"
    folder.mkdir()
    append_listing(str(folder), title="Mein Buch", author="A", book_title="B",
                   language="Deutsch", description="D", price="9.99",
                   condition_id="5000", picture_urls=["https://x/1.jpg"])
    c.post("/api/settings", json={"save_folder": str(folder)})
    r = c.get("/api/listings")
    assert r.status_code == 200
    listings = r.get_json()["listings"]
    assert listings[0]["title"] == "Mein Buch"

def test_listings_ohne_ordner_leer(tmp_path):
    c = _client(tmp_path)
    r = c.get("/api/listings")
    assert r.status_code == 200
    assert r.get_json()["listings"] == []

def test_mark_uploaded_archiviert_und_leert(tmp_path):
    from ebay_csv import append_listing
    c = _client(tmp_path)
    folder = tmp_path / "out"
    folder.mkdir()
    append_listing(str(folder), title="Mein Buch", author="A", book_title="B",
                   language="Deutsch", description="D", price="9.99",
                   condition_id="5000", picture_urls=["https://x/1.jpg"])
    c.post("/api/settings", json={"save_folder": str(folder)})
    r = c.post("/api/mark-uploaded")
    assert r.status_code == 200
    assert r.get_json()["moved"] == 1
    assert c.get("/api/listings").get_json()["listings"] == []   # Liste jetzt leer

def test_mark_uploaded_ohne_ordner_fehler(tmp_path):
    c = _client(tmp_path)
    r = c.post("/api/mark-uploaded")
    assert r.status_code == 400

def test_create_csv_fragt_bei_dublette(tmp_path):
    from ebay_csv import append_listing
    c = _client(tmp_path)
    folder = tmp_path / "out"
    folder.mkdir()
    append_listing(str(folder), title="Mein Buch", author="A", book_title="B",
                   language="Deutsch", description="D", price="9.99",
                   condition_id="5000", picture_urls=["https://x/1.jpg"])
    c.post("/api/settings", json={"imgbb_api_key": "k", "save_folder": str(folder)})
    data = {"title": "Mein Buch", "images": (io.BytesIO(b"\xff\xd8jpeg"), "1.jpg")}
    with patch("app.upload_image") as up:
        r = c.post("/api/create-csv", data=data, content_type="multipart/form-data")
    body = r.get_json()
    assert r.status_code == 200
    assert body.get("duplicate") is True
    assert body["title"] == "Mein Buch"
    assert not up.called                       # kein Foto-Upload auf dem Abbruch-Pfad

def test_create_csv_overwrite_ersetzt(tmp_path):
    from ebay_csv import append_listing
    c = _client(tmp_path)
    folder = tmp_path / "out"
    folder.mkdir()
    append_listing(str(folder), title="Mein Buch", author="A", book_title="B",
                   language="Deutsch", description="D", price="9.99",
                   condition_id="5000", picture_urls=["https://x/1.jpg"])
    c.post("/api/settings", json={"imgbb_api_key": "k", "save_folder": str(folder)})
    data = {"title": "Mein Buch", "overwrite": "true", "price": "5.00",
            "images": (io.BytesIO(b"\xff\xd8jpeg"), "1.jpg")}
    with patch("app.upload_image", return_value="https://img/1.jpg"):
        r = c.post("/api/create-csv", data=data, content_type="multipart/form-data")
    body = r.get_json()
    assert r.status_code == 200
    assert body["ok"] is True
    assert body["count"] == 1                   # ersetzt, nicht zusätzlich angehängt

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
    # Text-Aufruf nutzt das Text-Modell (Standard Opus).
    assert m.call_args.kwargs["model"] == "claude-opus-4-8"

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
    fake = PriceAnalysis(comparables=[{"title": "X", "price": "12.00",
                                       "url": "https://y", "source": "ZVAB"}],
                         note="ok")
    with patch("app.analyze_price", return_value=fake) as m:
        r = c.post("/api/price", json={"author": "A", "book_title": "B", "title": "T",
                                       "language": "Deutsch", "publication_year": "1957",
                                       "publisher": "", "book_format": ""})
    assert r.status_code == 200
    assert r.get_json()["comparables"][0]["price"] == "12.00"
    assert m.called
    # Preis-Aufruf nutzt das (schnellere) Preis-Modell (Standard Sonnet).
    assert m.call_args.kwargs["model"] == "claude-sonnet-4-6"
