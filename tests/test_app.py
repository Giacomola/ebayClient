import io
from unittest.mock import patch
from app import create_app
from ai_client import BookFields
from price_analysis import PriceAnalysis
from derive_instructions import DerivedInstructions

def _client(tmp_path):
    # draft_path und cases_dir mit isolieren, damit Tests weder die echte
    # draft.json verändern noch einen echten cases/-Ordner anlegen.
    app = create_app(config_path=str(tmp_path / "config.json"),
                     draft_path=str(tmp_path / "draft.json"),
                     cases_dir=str(tmp_path / "cases"))
    app.config.update(TESTING=True)
    return app.test_client()

def test_startseite_oeffnet_links_in_neuem_tab(tmp_path):
    c = _client(tmp_path)
    html = c.get("/").get_data(as_text=True)
    assert '<base target="_blank">' in html   # alle Links im neuen Tab

def test_startseite_zeigt_version(tmp_path):
    from app import APP_VERSION
    c = _client(tmp_path)
    html = c.get("/").get_data(as_text=True)
    assert f"v{APP_VERSION}" in html          # Version oben im Kopf (z. B. v1.0)
    assert "Stand:" not in html               # die alte Datumsanzeige ist weg

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

def test_draft_images_rev_und_live_abfrage(tmp_path):
    c = _client(tmp_path)
    assert c.get("/api/draft/images-rev").get_json()["images_rev"] == 0
    data = {"images": (io.BytesIO(b"\xff\xd8jpeg"), "1.jpg")}
    r = c.post("/api/draft/images", data=data, content_type="multipart/form-data")
    body = r.get_json()
    assert body["images_rev"] == 1                      # Antwort enthält neue Version
    rev = c.get("/api/draft/images-rev").get_json()
    assert rev["images_rev"] == 1 and rev["count"] == 1  # leichte Abfrage stimmt überein

def test_handy_zugang_mit_ip(tmp_path):
    c = _client(tmp_path)
    with patch("app._lan_ip", return_value="192.168.0.5"):
        r = c.get("/api/handy-zugang")
    body = r.get_json()
    assert r.status_code == 200
    assert body["url"] == "http://192.168.0.5:5050"
    assert not body.get("error")

def test_handy_zugang_ohne_netz(tmp_path):
    c = _client(tmp_path)
    with patch("app._lan_ip", return_value=""):
        r = c.get("/api/handy-zugang")
    body = r.get_json()
    assert r.status_code == 200
    assert body["url"] == ""
    assert body["error"]

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

def test_archive_file_archiviert_und_beginnt_neu(tmp_path):
    from ebay_csv import append_listing
    c = _client(tmp_path)
    folder = tmp_path / "out"
    folder.mkdir()
    append_listing(str(folder), title="Mein Buch", author="A", book_title="B",
                   language="Deutsch", description="D", price="9.99",
                   condition_id="5000", picture_urls=["https://x/1.jpg"])
    c.post("/api/settings", json={"save_folder": str(folder)})
    r = c.post("/api/archive-file", json={"name": "Romane"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["moved"] == 1
    assert body["filename"].startswith("eBayClient_") and body["filename"].endswith("_Romane.csv")
    assert c.get("/api/listings").get_json()["listings"] == []   # Liste jetzt leer

def test_archive_file_leer_gibt_fehler(tmp_path):
    c = _client(tmp_path)
    folder = tmp_path / "leer"
    folder.mkdir()
    c.post("/api/settings", json={"save_folder": str(folder)})
    r = c.post("/api/archive-file", json={"name": ""})
    assert r.status_code == 400

def test_archive_file_ohne_ordner_fehler(tmp_path):
    c = _client(tmp_path)
    r = c.post("/api/archive-file", json={"name": ""})
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
    # Anderer Anzeigentitel, aber gleicher Autor+Buchtitel -> trotzdem Dublette.
    data = {"title": "Mein Buch (leicht anders)", "author": "A", "book_title": "B",
            "images": (io.BytesIO(b"\xff\xd8jpeg"), "1.jpg")}
    with patch("app.upload_image") as up:
        r = c.post("/api/create-csv", data=data, content_type="multipart/form-data")
    body = r.get_json()
    assert r.status_code == 200
    assert body.get("duplicate") is True
    assert body["title"] == "B – A"            # Label aus Buchtitel + Autor
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
    data = {"title": "Mein Buch neu", "author": "A", "book_title": "B",
            "overwrite": "true", "price": "5.00",
            "images": (io.BytesIO(b"\xff\xd8jpeg"), "1.jpg")}
    with patch("app.upload_image", return_value="https://img/1.jpg"):
        r = c.post("/api/create-csv", data=data, content_type="multipart/form-data")
    body = r.get_json()
    assert r.status_code == 200
    assert body["ok"] is True
    assert body["count"] == 1                   # ersetzt (gleicher Autor+Buchtitel), nicht angehängt

def _add_listing(c, folder, title="Mein Buch"):
    """Legt über die echte create-csv-Route eine Anzeige an (Foto-Upload gemockt)."""
    c.post("/api/settings", json={"imgbb_api_key": "k", "save_folder": str(folder)})
    data = {"title": title, "author": "A", "book_title": "B", "language": "Deutsch",
            "description": "D", "price": "9.99", "condition_id": "5000",
            "images": (io.BytesIO(b"\xff\xd8jpeg"), "1.jpg")}
    with patch("app.upload_image", return_value="https://img/1.jpg"):
        return c.post("/api/create-csv", data=data, content_type="multipart/form-data")

def test_create_csv_legt_bearbeitbaren_fall_an(tmp_path):
    c = _client(tmp_path)
    folder = tmp_path / "out"; folder.mkdir()
    assert _add_listing(c, folder).status_code == 200
    listings = c.get("/api/listings").get_json()["listings"]
    assert listings[0]["title"] == "Mein Buch"
    cid = listings[0]["case_id"]
    assert cid                                   # bearbeitbarer Fall liegt vor
    # Der Fall taucht NICHT in „Fall wiederaufnehmen" auf (nur offene Fälle dort).
    assert c.get("/api/cases").get_json()["cases"] == []
    # Öffnen zum Bearbeiten darf den in_csv-Fall nicht verbrauchen.
    assert c.post(f"/api/cases/{cid}/open").status_code == 200
    listings2 = c.get("/api/listings").get_json()["listings"]
    assert listings2[0]["case_id"] == cid        # Fall besteht weiter

def test_overview_buendelt_alles(tmp_path):
    c = _client(tmp_path)
    folder = tmp_path / "out"; folder.mkdir()
    _add_listing(c, folder, title="Mein Buch")
    ov = c.get("/api/overview").get_json()
    assert ov["stats"]["count"] == 1
    assert ov["listings"][0]["title"] == "Mein Buch"
    assert ov["listings"][0]["case_id"]            # bearbeitbar
    assert ov["active_cases"] == []                # nichts in Arbeit
    assert ov["archives"] == []                    # noch nichts archiviert
    c.post("/api/archive-file", json={"name": "Romane"})
    ov2 = c.get("/api/overview").get_json()
    assert ov2["stats"]["count"] == 0              # Sammeldatei leer
    assert len(ov2["archives"]) == 1               # eine archivierte Datei
    assert ov2["archives"][0]["filename"].startswith("eBayClient_")

def test_archive_entfernt_bearbeitbare_faelle(tmp_path):
    c = _client(tmp_path)
    folder = tmp_path / "out"; folder.mkdir()
    _add_listing(c, folder)
    assert c.get("/api/listings").get_json()["listings"][0]["case_id"]
    r = c.post("/api/archive-file", json={"name": "Romane"})
    assert r.status_code == 200
    # CSV ist leer und der zugehörige bearbeitbare Fall wurde mit aufgeräumt.
    assert c.get("/api/listings").get_json()["listings"] == []

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

def test_generate_analysiert_hoechstens_5_fotos(tmp_path):
    c = _client(tmp_path)
    c.post("/api/settings", json={"anthropic_api_key": "sk-x"})
    fake = BookFields(title="T", author="A", book_title="B", language="Deutsch",
                      description="D")
    # Acht Fotos schicken – das Backend darf höchstens 5 an die KI weiterreichen.
    data = {"images": [(io.BytesIO(b"\xff\xd8jpeg"), f"{i}.jpg") for i in range(8)]}
    with patch("app.analyze_book", return_value=fake) as m:
        r = c.post("/api/generate", data=data, content_type="multipart/form-data")
    assert r.status_code == 200
    assert len(m.call_args.args[0]) == 5    # nur 5 Bilder kamen bei der KI an

def _status_error(cls, status, message):
    import httpx
    resp = httpx.Response(status, request=httpx.Request("POST", "http://x"))
    return cls(message, response=resp, body=None)

def test_generate_token_limit_429(tmp_path):
    c = _client(tmp_path)
    c.post("/api/settings", json={"anthropic_api_key": "sk-x"})
    import anthropic
    err = _status_error(anthropic.RateLimitError, 429, "rate limit exceeded")
    with patch("app.analyze_book", side_effect=err):
        data = {"images": (io.BytesIO(b"\xff\xd8jpeg"), "1.jpg")}
        r = c.post("/api/generate", data=data, content_type="multipart/form-data")
    assert r.status_code == 429
    assert "Limit" in r.get_json()["error"]

def test_generate_eingabe_zu_gross_413(tmp_path):
    c = _client(tmp_path)
    c.post("/api/settings", json={"anthropic_api_key": "sk-x"})
    import anthropic
    err = _status_error(anthropic.BadRequestError, 400,
                        "prompt is too long: 250000 tokens > 200000 maximum")
    with patch("app.analyze_book", side_effect=err):
        data = {"images": (io.BytesIO(b"\xff\xd8jpeg"), "1.jpg")}
        r = c.post("/api/generate", data=data, content_type="multipart/form-data")
    assert r.status_code == 413
    assert "Token-Limit" in r.get_json()["error"]

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
                         recommended_price="11.50", price_reason="Gut erhalten", note="ok")
    with patch("app.analyze_price", return_value=fake) as m:
        r = c.post("/api/price", json={"author": "A", "book_title": "B", "title": "T",
                                       "language": "Deutsch", "publication_year": "1957",
                                       "publisher": "", "book_format": "", "condition": "Gut"})
    assert r.status_code == 200
    body = r.get_json()
    assert body["comparables"][0]["price"] == "12.00"
    assert body["recommended_price"] == "11.50"   # Empfehlung wird durchgereicht
    assert body["price_reason"] == "Gut erhalten"
    assert m.called
    # Preis-Aufruf nutzt das (schnellere) Preis-Modell (Standard Sonnet).
    assert m.call_args.kwargs["model"] == "claude-sonnet-4-6"
    assert m.call_args.kwargs["condition"] == "Gut"   # Zustand wird mitgegeben

def test_derive_instructions_fuellt_felder(tmp_path):
    c = _client(tmp_path)
    c.post("/api/settings", json={"anthropic_api_key": "x"})
    fake = DerivedInstructions(prompt_general="REGELN", description="BESCHREIBUNG")
    with patch("app.derive_from_example", return_value=fake) as m:
        r = c.post("/api/derive-instructions", json={"example": "Ein Mustertext."})
    assert r.status_code == 200
    body = r.get_json()
    assert body["prompt_general"] == "REGELN"
    assert body["description"] == "BESCHREIBUNG"
    assert m.called
    # nutzt das Textmodell und reicht das Beispiel als erstes Argument durch.
    assert m.call_args.kwargs["model"] == "claude-opus-4-8"
    assert m.call_args.args[0] == "Ein Mustertext."

def test_derive_instructions_leeres_beispiel_400(tmp_path):
    c = _client(tmp_path)
    c.post("/api/settings", json={"anthropic_api_key": "x"})
    r = c.post("/api/derive-instructions", json={"example": "   "})
    assert r.status_code == 400
    assert "Beispiel" in r.get_json()["error"]

def test_chat_ohne_schluessel_gibt_fehler(tmp_path):
    c = _client(tmp_path)
    r = c.post("/api/chat", json={"messages": [{"role": "user", "content": "Hallo"}]})
    assert r.status_code == 400
    assert "Schlüssel" in r.get_json()["error"]

def test_chat_ruft_modell_und_gibt_antwort(tmp_path):
    c = _client(tmp_path)
    c.post("/api/settings", json={"anthropic_api_key": "sk-x", "model_chat": "claude-haiku-4-5"})
    with patch("app.chat", return_value="Hallo, wie kann ich helfen?") as m:
        r = c.post("/api/chat", json={"messages": [{"role": "user", "content": "Hi"}]})
    assert r.status_code == 200
    assert r.get_json()["answer"].startswith("Hallo")
    assert m.called
    assert m.call_args.kwargs["model"] == "claude-haiku-4-5"   # eingestelltes Chat-Modell
    assert m.call_args.kwargs["modellname"] == "Haiku"         # stellt sich mit Namen vor

def test_chat_leer_gibt_fehler(tmp_path):
    c = _client(tmp_path)
    c.post("/api/settings", json={"anthropic_api_key": "sk-x"})
    r = c.post("/api/chat", json={"messages": []})
    assert r.status_code == 400

def test_chat_kennt_gespeicherte_faelle(tmp_path):
    # Der Chat bekommt den aktuellen Stand der Einträge ins Wissen gereicht.
    c = _client(tmp_path)
    c.post("/api/settings", json={"anthropic_api_key": "sk-x"})
    _save_offenen_fall(c, "Faust")
    c.post("/api/draft/clear")   # parkt den Fall als offenen Fall
    with patch("app.chat", return_value="ok") as m:
        c.post("/api/chat", json={"messages": [{"role": "user", "content": "Welche Fälle?"}]})
    wissen = m.call_args.kwargs["wissen"]
    assert "Goethe – Faust" in wissen          # der offene Fall steht im Wissen
    assert "Offene Fälle" in wissen            # der aktuelle Stand ist angehängt
    assert "Ablauf" in wissen                  # die feste App-Beschreibung auch

# --- Aktive Fälle (parken / öffnen / löschen) -------------------------------

def _save_offenen_fall(c, title="Faust"):
    """Legt einen offenen Fall mit Foto und Titel in der aktuellen draft.json an."""
    c.post("/api/draft", json={"fields": {"title": title, "author": "Goethe",
                                          "book_title": title}, "result_visible": True})
    c.post("/api/draft/images", data={"images": (io.BytesIO(b"\xff\xd8jpeg"), "1.jpg")},
           content_type="multipart/form-data")

def test_neuer_fall_parkt_offenen_fall(tmp_path):
    c = _client(tmp_path)
    _save_offenen_fall(c, "Faust")
    r = c.post("/api/draft/clear")
    assert r.get_json()["parked"] is True
    cases = c.get("/api/cases").get_json()["cases"]
    assert len(cases) == 1
    assert cases[0]["name"] == "Goethe – Faust"
    assert cases[0]["photo_count"] == 1
    # draft.json ist jetzt leer für den neuen Fall
    assert c.get("/api/draft").get_json()["fields"] == {}

def test_neuer_fall_parkt_leeren_fall_nicht(tmp_path):
    c = _client(tmp_path)
    r = c.post("/api/draft/clear")
    assert r.get_json()["parked"] is False
    assert c.get("/api/cases").get_json()["cases"] == []

def test_abgeschlossener_fall_wird_nicht_geparkt(tmp_path):
    c = _client(tmp_path)
    _save_offenen_fall(c, "Werther")
    # Fall in die Sammeldatei übernehmen -> gilt als abgeschlossen
    folder = tmp_path / "out"
    folder.mkdir()
    c.post("/api/settings", json={"imgbb_api_key": "k", "save_folder": str(folder)})
    with patch("app.upload_image", return_value="https://img/1.jpg"):
        c.post("/api/create-csv",
               data={"title": "Werther", "images": (io.BytesIO(b"\xff\xd8jpeg"), "1.jpg")},
               content_type="multipart/form-data")
    r = c.post("/api/draft/clear")
    assert r.get_json()["parked"] is False          # abgeschlossen -> nicht parken
    assert c.get("/api/cases").get_json()["cases"] == []

def test_fall_oeffnen_macht_ihn_zum_aktuellen(tmp_path):
    c = _client(tmp_path)
    _save_offenen_fall(c, "Faust")
    c.post("/api/draft/clear")                       # Faust parken, neu beginnen
    cid = c.get("/api/cases").get_json()["cases"][0]["id"]
    r = c.post(f"/api/cases/{cid}/open")
    assert r.status_code == 200
    assert c.get("/api/draft").get_json()["fields"]["book_title"] == "Faust"
    assert c.get("/api/cases").get_json()["cases"] == []   # nicht mehr in der Liste

def test_fall_oeffnen_parkt_aktuellen_offenen(tmp_path):
    c = _client(tmp_path)
    _save_offenen_fall(c, "Faust")
    c.post("/api/draft/clear")                       # Faust geparkt
    _save_offenen_fall(c, "Werther")                 # neuer offener Fall im draft
    cid = c.get("/api/cases").get_json()["cases"][0]["id"]   # Faust
    c.post(f"/api/cases/{cid}/open")
    # Faust ist jetzt aktiv, Werther wurde dabei geparkt
    assert c.get("/api/draft").get_json()["fields"]["book_title"] == "Faust"
    namen = [x["name"] for x in c.get("/api/cases").get_json()["cases"]]
    assert namen == ["Goethe – Werther"]

def test_fall_oeffnen_unbekannt_404(tmp_path):
    c = _client(tmp_path)
    r = c.post("/api/cases/case_999/open")
    assert r.status_code == 404

def test_fall_loeschen(tmp_path):
    c = _client(tmp_path)
    _save_offenen_fall(c, "Faust")
    c.post("/api/draft/clear")
    cid = c.get("/api/cases").get_json()["cases"][0]["id"]
    r = c.post(f"/api/cases/{cid}/delete")
    assert r.get_json()["ok"] is True
    assert c.get("/api/cases").get_json()["cases"] == []

def test_preis_ergebnis_wird_gespeichert_und_geladen(tmp_path):
    c = _client(tmp_path)
    pr = {"comparables": [{"title": "X", "price": "10"}], "recommended_price": "9.50"}
    r = c.post("/api/draft/price", json={"price_result": pr})
    assert r.status_code == 200
    assert c.get("/api/draft").get_json()["price_result"]["recommended_price"] == "9.50"

def test_fall_oeffnen_nimmt_preis_ergebnis_mit(tmp_path):
    c = _client(tmp_path)
    _save_offenen_fall(c, "Faust")
    c.post("/api/draft/price", json={"price_result": {"recommended_price": "12.00"}})
    c.post("/api/draft/clear")                                  # Fall parken
    cid = c.get("/api/cases").get_json()["cases"][0]["id"]
    c.post(f"/api/cases/{cid}/open")                            # wieder aufnehmen
    assert c.get("/api/draft").get_json()["price_result"]["recommended_price"] == "12.00"
