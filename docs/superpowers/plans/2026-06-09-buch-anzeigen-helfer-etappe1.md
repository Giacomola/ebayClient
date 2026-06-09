# Buch-Anzeigen-Helfer – Etappe 1 – Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Einfache Codieraufgaben an Sonnet-Subagenten delegieren; Planung/Debugging bleibt beim Opus-Hauptagenten.

**Goal:** Eine lokale Web-App, die aus Fotos eines Buches per Claude einen eBay-Anzeigentext erzeugt, in bearbeitbarer Vorschau zeigt und als fertige eBay-File-Exchange-CSV ausgibt (Fotos automatisch über imgbb gehostet).

**Architecture:** Kleines Flask-Backend (Python) mit Browser-Oberfläche. Vier klar getrennte Module: `config` (Einstellungen/Schlüssel), `ai_client` (Claude-Vision → strukturierte Buchfelder), `image_host` (imgbb-Upload), `ebay_csv` (exaktes File-Exchange-CSV). Frontend: eine Seite mit Drag&Drop, Vorschau-Feldern und Export-Knopf.

**Tech Stack:** Python 3.11+, Flask, anthropic (offizielles SDK), requests, pytest. Frontend: HTML/CSS/Vanilla-JS.

**Bestätigte Fakten (aus Spec, Abschnitt 11):** CSV = UTF-8 **mit BOM**, Trennzeichen `;`, Zeile1 `Info;Version=1.0.0;Template=fx_category_template_EBAY_DE`, Zeile2 exakte 99-Spalten-Kopfzeile, Aktion `Add`, Kategorie `261186`, Zustands-IDs Bücher 1000/2750/4000/5000/6000, Versand/Rücknahme inline (keine Business Policies). Fotos als `PicURL` (öffentliche Adresse, eBay re-hostet).

---

## File Structure

```
ebay-client/
  requirements.txt          # Abhängigkeiten
  config.py                 # Einstellungen laden/speichern (config.json) + DEFAULT_PROMPT
  ebay_csv.py               # build_csv(...) -> bytes  (File-Exchange-Format)  [Kern, TDD]
  image_host.py             # upload_image(bytes, key) -> url  (imgbb)         [TDD, Mock]
  ai_client.py              # BookFields + analyze_book(images, ...) (Claude)  [TDD, Mock]
  app.py                    # Flask-Routen, verdrahtet die Module
  templates/index.html      # Oberfläche
  static/style.css          # Gestaltung
  static/app.js             # Drag&Drop, Aufrufe, Download
  tests/test_ebay_csv.py
  tests/test_config.py
  tests/test_image_host.py
  tests/test_ai_client.py
  tests/test_app.py
  README.md
```

Jede Datei hat eine Aufgabe. `ebay_csv`, `image_host`, `config`, `ai_client` sind reine, einzeln testbare Module; `app.py` verdrahtet nur.

---

## Task 0: Projektgerüst

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: requirements.txt anlegen**

```
Flask>=3.0
anthropic>=0.69
requests>=2.32
pytest>=8.0
```

> Hinweis: `ai_client` nutzt `client.messages.parse(..., output_format=...)`. Sollte die
> installierte anthropic-Version das nicht kennen, auf `messages.create` mit
> `output_config={"format": {"type": "json_schema", "schema": ...}}` + `json.loads` ausweichen.

- [ ] **Step 2: Virtuelle Umgebung + Installation**

Run:
```bash
cd /Users/giacomolanda/Desktop/ebay-client
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```
Expected: Installation ohne Fehler.

- [ ] **Step 3: pytest-Lauf (noch keine Tests)**

Run: `. .venv/bin/activate && pytest -q`
Expected: „no tests ran" (kein Fehler).

- [ ] **Step 4: Commit**

```bash
git init
git add requirements.txt
git commit -m "chore: Projektgerüst und Abhängigkeiten"
```

> Hinweis: Falls noch kein Git-Repo gewünscht ist, mit dem Nutzer abklären (CLAUDE.md-Regel 6). Andernfalls dieses init/commit weglassen.

---

## Task 1: config.py – Einstellungen laden/speichern

**Files:**
- Create: `config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Failing Test schreiben**

```python
# tests/test_config.py
import json
from config import load_settings, save_settings, DEFAULTS

def test_load_missing_file_returns_defaults(tmp_path):
    p = tmp_path / "config.json"
    settings = load_settings(str(p))
    assert settings["model"] == "claude-sonnet-4-6"
    assert settings["anthropic_api_key"] == ""

def test_save_then_load_roundtrip(tmp_path):
    p = tmp_path / "config.json"
    save_settings({"anthropic_api_key": "sk-test", "model": "claude-opus-4-8"}, str(p))
    loaded = load_settings(str(p))
    assert loaded["anthropic_api_key"] == "sk-test"
    assert loaded["model"] == "claude-opus-4-8"
    # fehlende Felder werden mit Defaults ergänzt
    assert loaded["shipping_service"] == "DE_DHLPaket"
```

- [ ] **Step 2: Test laufen lassen (muss fehlschlagen)**

Run: `pytest tests/test_config.py -v`
Expected: FAIL (`ModuleNotFoundError: config`).

- [ ] **Step 3: config.py implementieren**

```python
# config.py
import json
import os

DEFAULT_PROMPT = (
    "Du bist ein Assistent für eBay-Buchverkäufe. Analysiere die Fotos EINES Buches "
    "(Cover, Buchrücken, ggf. Impressum/Titelseite) und liefere die Felder für die "
    "Anzeige. Schreibe auf Deutsch, sachlich und korrekt. Der Titel (title) ist ein "
    "verkaufsstarker eBay-Anzeigentitel mit höchstens 80 Zeichen ohne Semikolons. "
    "book_title ist der reine Buchtitel, author der/die Autor(en), language die Sprache "
    "des Buches (z. B. Deutsch). description ist eine kurze, ehrliche Beschreibung des "
    "Artikels und des Autors (2-4 Sätze, keine Semikolons, keine Zeilenumbrüche-Pflicht). "
    "publisher, publication_year und book_format nur ausfüllen, wenn sicher erkennbar, "
    "sonst leer lassen."
)

DEFAULTS = {
    "anthropic_api_key": "",
    "imgbb_api_key": "",
    "model": "claude-sonnet-4-6",
    "location": "Berlin",
    "shipping_service": "DE_DHLPaket",
    "shipping_cost": "5.49",
    "dispatch_time_max": "3",
    "prompt": DEFAULT_PROMPT,
}

def load_settings(path: str = "config.json") -> dict:
    settings = dict(DEFAULTS)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            settings.update(json.load(f))
    return settings

def save_settings(settings: dict, path: str = "config.json") -> None:
    merged = dict(DEFAULTS)
    merged.update(settings)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
```

- [ ] **Step 4: Test laufen lassen (muss bestehen)**

Run: `pytest tests/test_config.py -v`
Expected: PASS (2 Tests).

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: config laden/speichern mit Defaults"
```

---

## Task 2: ebay_csv.py – exaktes File-Exchange-CSV (Kernmodul)

**Files:**
- Create: `ebay_csv.py`
- Test: `tests/test_ebay_csv.py`

- [ ] **Step 1: Failing Tests schreiben**

```python
# tests/test_ebay_csv.py
from ebay_csv import build_csv, COLUMNS

def _parse(data: bytes):
    assert data[:3] == b"\xef\xbb\xbf"            # BOM vorhanden
    text = data.decode("utf-8-sig")
    return text.splitlines()

def test_struktur_bom_und_99_spalten():
    data = build_csv(
        title="Der Hobbit guter Zustand", author="J.R.R. Tolkien",
        book_title="Der Hobbit", language="Deutsch", description="Gut erhalten.",
        price="9.99", condition_id="5000",
        picture_urls=["https://i.ibb.co/abc/1.jpg"],
    )
    lines = _parse(data)
    assert lines[0].startswith("Info;Version=1.0.0;Template=fx_category_template_EBAY_DE")
    header = lines[1].split(";")
    row = lines[2].split(";")
    assert len(header) == 99
    assert len(row) == 99
    assert row[0] == "Add"

def test_felder_an_richtiger_stelle():
    data = build_csv(
        title="T", author="A", book_title="B", language="Deutsch",
        description="D", price="12.50", condition_id="4000",
        picture_urls=["https://x/1.jpg", "https://x/2.jpg"],
    )
    lines = _parse(data)
    header = lines[1].split(";")
    row = dict(zip(header, lines[2].split(";")))
    assert row["*Category"] == "261186"
    assert row["*ConditionID"] == "4000"
    assert row["*C:Autor"] == "A"
    assert row["*StartPrice"] == "12.50"
    assert row["PicURL"] == "https://x/1.jpg|https://x/2.jpg"
    assert row["*ReturnsAcceptedOption"] == "ReturnsNotAccepted"

def test_semikolon_und_titel_werden_bereinigt():
    langer_titel = "X" * 100
    data = build_csv(
        title=langer_titel, author="A", book_title="B", language="Deutsch",
        description="Zeile1; mit Semikolon\nund Umbruch", price="9.99",
        condition_id="5000", picture_urls=["https://x/1.jpg"],
    )
    lines = _parse(data)
    # 99 Felder trotz Semikolon in der Beschreibung
    assert len(lines[2].split(";")) == 99
    header = lines[1].split(";")
    row = dict(zip(header, lines[2].split(";")))
    assert ";" not in row["*Description"]
    assert len(row["*Title"]) <= 80
```

- [ ] **Step 2: Tests laufen lassen (müssen fehlschlagen)**

Run: `pytest tests/test_ebay_csv.py -v`
Expected: FAIL (`ModuleNotFoundError: ebay_csv`).

- [ ] **Step 3: ebay_csv.py implementieren**

```python
# ebay_csv.py
"""Erzeugt eine eBay-File-Exchange-CSV (Kategorie-Vorlage Bücher) für genau ein Buch."""

ACTION = "*Action(SiteID=Germany|Country=DE|Currency=EUR|Version=1193|CC=UTF-8)"
INFO_LINE = "Info;Version=1.0.0;Template=fx_category_template_EBAY_DE"

COLUMNS = [
    ACTION, "CustomLabel", "*Category", "StoreCategory", "*Title", "Subtitle",
    "Relationship", "RelationshipDetails", "ScheduleTime", "*ConditionID", "VAT%",
    "*C:Autor", "*C:Buchtitel", "*C:Sprache", "C:Thematik", "C:Buchreihe", "C:Genre",
    "C:Verlag", "C:Erscheinungsjahr", "C:Originalsprache", "C:Format", "C:Ursprungsland",
    "C:Produktart", "C:Literarische Gattung", "C:Signiert von", "C:Zielgruppe",
    "C:Ausgabe", "C:Literarische Bewegung", "C:Vintage", "C:Signiert", "C:Personalisiert",
    "C:Personalisieren", "C:Beschriftet", "C:Exlibris", "C:Besonderheiten", "C:Illustrator",
    "C:Epoche", "C:Herstellungszeitraum", "C:Anzahl der Einheiten", "C:Anzahl der Seiten",
    "C:Breite", "C:Gewicht", "C:Höhe", "C:Länge", "C:Maßeinheit",
    "C:Anleitung für Personalisierung", "PicURL", "GalleryType", "VideoID", "*Description",
    "*Format", "*Duration", "*StartPrice", "BuyItNowPrice", "BestOfferEnabled",
    "BestOfferAutoAcceptPrice", "MinimumBestOfferPrice", "*Quantity", "ImmediatePayRequired",
    "*Location", "ShippingType", "ShippingService-1:Option", "ShippingService-1:Cost",
    "ShippingService-2:Option", "ShippingService-2:Cost", "*DispatchTimeMax",
    "PromotionalShippingDiscount", "ShippingDiscountProfileID", "DomesticRateTable",
    "*ReturnsAcceptedOption", "ReturnsWithinOption", "RefundOption",
    "ShippingCostPaidByOption", "AdditionalDetails", "Product Safety Pictograms",
    "Product Safety Statements", "Product Safety Component", "Regulatory Document Ids",
    "Manufacturer Name", "Manufacturer AddressLine1", "Manufacturer AddressLine2",
    "Manufacturer City", "Manufacturer Country", "Manufacturer PostalCode",
    "Manufacturer StateOrProvince", "Manufacturer Phone", "Manufacturer Email",
    "Manufacturer ContactURL", "Responsible Person 1", "Responsible Person 1 Type",
    "Responsible Person 1 AddressLine1", "Responsible Person 1 AddressLine2",
    "Responsible Person 1 City", "Responsible Person 1 Country",
    "Responsible Person 1 PostalCode", "Responsible Person 1 StateOrProvince",
    "Responsible Person 1 Phone", "Responsible Person 1 Email",
    "Responsible Person 1 ContactURL",
]

def _clean(value) -> str:
    """Entfernt Trennzeichen/Umbrüche, damit die Spaltenanzahl stabil bleibt."""
    if value is None:
        return ""
    text = str(value)
    for ch in (";", "\r", "\n"):
        text = text.replace(ch, " ")
    return text.strip()

def build_csv(*, title, author, book_title, language, description, price,
              condition_id, picture_urls, publisher="", publication_year="",
              book_format="", location="Berlin", shipping_service="DE_DHLPaket",
              shipping_cost="5.49", dispatch_time_max="3", custom_label="") -> bytes:
    values = {
        ACTION: "Add",
        "CustomLabel": _clean(custom_label),
        "*Category": "261186",
        "*Title": _clean(title)[:80],
        "*ConditionID": _clean(condition_id),
        "*C:Autor": _clean(author),
        "*C:Buchtitel": _clean(book_title),
        "*C:Sprache": _clean(language),
        "C:Verlag": _clean(publisher),
        "C:Erscheinungsjahr": _clean(publication_year),
        "C:Format": _clean(book_format),
        "PicURL": "|".join(picture_urls[:12]),
        "*Description": _clean(description),
        "*Format": "FixedPrice",
        "*Duration": "GTC",
        "*StartPrice": _clean(price),
        "*Quantity": "1",
        "*Location": _clean(location),
        "ShippingType": "Flat",
        "ShippingService-1:Option": _clean(shipping_service),
        "ShippingService-1:Cost": _clean(shipping_cost),
        "*DispatchTimeMax": _clean(dispatch_time_max),
        "*ReturnsAcceptedOption": "ReturnsNotAccepted",
    }
    header = ";".join(COLUMNS)
    row = ";".join(values.get(col, "") for col in COLUMNS)
    text = "\r\n".join([INFO_LINE, header, row]) + "\r\n"
    return ("﻿" + text).encode("utf-8")
```

- [ ] **Step 4: Tests laufen lassen (müssen bestehen)**

Run: `pytest tests/test_ebay_csv.py -v`
Expected: PASS (3 Tests).

- [ ] **Step 5: Commit**

```bash
git add ebay_csv.py tests/test_ebay_csv.py
git commit -m "feat: eBay File-Exchange CSV-Erzeugung mit BOM und 99 Spalten"
```

---

## Task 3: image_host.py – imgbb-Upload

**Files:**
- Create: `image_host.py`
- Test: `tests/test_image_host.py`

- [ ] **Step 1: Failing Test schreiben (mit Mock)**

```python
# tests/test_image_host.py
from unittest.mock import patch, MagicMock
from image_host import upload_image

def test_upload_image_gibt_url_zurueck():
    fake = MagicMock()
    fake.json.return_value = {"data": {"url": "https://i.ibb.co/abc/1.jpg"}}
    fake.raise_for_status.return_value = None
    with patch("image_host.requests.post", return_value=fake) as post:
        url = upload_image(b"\xff\xd8fakejpeg", "imgbb-key")
    assert url == "https://i.ibb.co/abc/1.jpg"
    # Schlüssel wurde mitgesendet
    assert post.call_args.kwargs["data"]["key"] == "imgbb-key"
```

- [ ] **Step 2: Test laufen lassen (muss fehlschlagen)**

Run: `pytest tests/test_image_host.py -v`
Expected: FAIL (`ModuleNotFoundError: image_host`).

- [ ] **Step 3: image_host.py implementieren**

```python
# image_host.py
"""Lädt ein Bild zu imgbb hoch und gibt die öffentliche URL zurück."""
import base64
import requests

IMGBB_ENDPOINT = "https://api.imgbb.com/1/upload"

def upload_image(image_bytes: bytes, api_key: str) -> str:
    encoded = base64.b64encode(image_bytes).decode("ascii")
    resp = requests.post(
        IMGBB_ENDPOINT,
        data={"key": api_key, "image": encoded},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["data"]["url"]
```

- [ ] **Step 4: Test laufen lassen (muss bestehen)**

Run: `pytest tests/test_image_host.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add image_host.py tests/test_image_host.py
git commit -m "feat: imgbb-Bildupload"
```

---

## Task 4: ai_client.py – Claude-Vision → Buchfelder

**Files:**
- Create: `ai_client.py`
- Test: `tests/test_ai_client.py`

- [ ] **Step 1: Failing Test schreiben (anthropic gemockt)**

```python
# tests/test_ai_client.py
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
    # Modell wurde durchgereicht
    assert fake_client.messages.parse.call_args.kwargs["model"] == "claude-sonnet-4-6"
```

- [ ] **Step 2: Test laufen lassen (muss fehlschlagen)**

Run: `pytest tests/test_ai_client.py -v`
Expected: FAIL (`ModuleNotFoundError: ai_client`).

- [ ] **Step 3: ai_client.py implementieren**

```python
# ai_client.py
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
```

- [ ] **Step 4: Test laufen lassen (muss bestehen)**

Run: `pytest tests/test_ai_client.py -v`
Expected: PASS (2 Tests).

- [ ] **Step 5: Commit**

```bash
git add ai_client.py tests/test_ai_client.py
git commit -m "feat: Claude-Vision-Analyse zu strukturierten Buchfeldern"
```

---

## Task 5: app.py – Flask-Routen (Verdrahtung)

**Files:**
- Create: `app.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Failing Tests schreiben**

```python
# tests/test_app.py
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
```

- [ ] **Step 2: Tests laufen lassen (müssen fehlschlagen)**

Run: `pytest tests/test_app.py -v`
Expected: FAIL (`ModuleNotFoundError: app`).

- [ ] **Step 3: app.py implementieren**

```python
# app.py
from flask import Flask, request, jsonify, render_template, Response
from config import load_settings, save_settings
from ai_client import analyze_book
from image_host import upload_image
from ebay_csv import build_csv

def create_app(config_path: str = "config.json") -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/settings")
    def get_settings():
        return jsonify(load_settings(config_path))

    @app.post("/api/settings")
    def post_settings():
        current = load_settings(config_path)
        current.update(request.get_json(force=True))
        save_settings(current, config_path)
        return jsonify({"ok": True})

    @app.post("/api/generate")
    def generate():
        settings = load_settings(config_path)
        if not settings["anthropic_api_key"]:
            return jsonify({"error": "Kein Anthropic-API-Schlüssel hinterlegt. "
                                     "Bitte in den Einstellungen eintragen."}), 400
        files = request.files.getlist("images")
        if not files:
            return jsonify({"error": "Keine Fotos ausgewählt."}), 400
        images = [f.read() for f in files]
        try:
            book = analyze_book(images, api_key=settings["anthropic_api_key"],
                                model=settings["model"], prompt=settings["prompt"])
        except Exception as e:  # noqa: BLE001 - dem Nutzer verständlich melden
            return jsonify({"error": f"KI-Fehler: {e}"}), 502
        return jsonify(book.model_dump())

    @app.post("/api/create-csv")
    def create_csv():
        settings = load_settings(config_path)
        if not settings["imgbb_api_key"]:
            return jsonify({"error": "Kein imgbb-API-Schlüssel hinterlegt. "
                                     "Bitte in den Einstellungen eintragen."}), 400
        form = request.form
        files = request.files.getlist("images")
        try:
            urls = [upload_image(f.read(), settings["imgbb_api_key"]) for f in files]
        except Exception as e:  # noqa: BLE001
            return jsonify({"error": f"Foto-Upload fehlgeschlagen: {e}"}), 502
        if not urls:
            return jsonify({"error": "Keine Fotos für die Anzeige vorhanden."}), 400
        csv_bytes = build_csv(
            title=form.get("title", ""), author=form.get("author", ""),
            book_title=form.get("book_title", ""), language=form.get("language", ""),
            description=form.get("description", ""), price=form.get("price", ""),
            condition_id=form.get("condition_id", ""), picture_urls=urls,
            publisher=form.get("publisher", ""),
            publication_year=form.get("publication_year", ""),
            book_format=form.get("book_format", ""),
            location=settings["location"], shipping_service=settings["shipping_service"],
            shipping_cost=settings["shipping_cost"],
            dispatch_time_max=settings["dispatch_time_max"],
        )
        return Response(
            csv_bytes, mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=ebay-anzeige.csv"},
        )

    return app

if __name__ == "__main__":
    import webbrowser
    app = create_app()
    webbrowser.open("http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)
```

- [ ] **Step 4: Tests laufen lassen (müssen bestehen)**

Run: `pytest tests/test_app.py -v`
Expected: PASS (3 Tests).

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat: Flask-Routen (settings, generate, create-csv)"
```

---

## Task 6: Oberfläche – index.html, style.css, app.js

**Files:**
- Create: `templates/index.html`
- Create: `static/style.css`
- Create: `static/app.js`

- [ ] **Step 1: templates/index.html anlegen**

```html
<!doctype html>
<html lang="de">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Buch-Anzeigen-Helfer</title>
  <link rel="stylesheet" href="/static/style.css">
</head>
<body>
  <header>
    <h1>Buch-Anzeigen-Helfer</h1>
    <button id="settings-btn" type="button">Einstellungen</button>
  </header>

  <main>
    <section id="drop-zone" class="drop-zone">
      <p>Fotos des Buches hierher ziehen</p>
      <input id="file-input" type="file" accept="image/*" multiple hidden>
      <button id="choose-btn" type="button">Fotos auswählen</button>
      <div id="thumbs" class="thumbs"></div>
    </section>

    <button id="generate-btn" type="button" class="primary" disabled>Anzeige erstellen</button>
    <p id="status" class="status"></p>

    <section id="result" class="result" hidden>
      <label>Titel <input id="f-title" maxlength="80"></label>
      <label>Autor <input id="f-author"></label>
      <label>Buchtitel <input id="f-book_title"></label>
      <label>Sprache <input id="f-language"></label>
      <label>Verlag <input id="f-publisher"></label>
      <label>Erscheinungsjahr <input id="f-publication_year"></label>
      <label>Format <input id="f-book_format"></label>
      <label>Beschreibung <textarea id="f-description" rows="4"></textarea></label>
      <label>Preis (EUR, z. B. 9.99) <input id="f-price" value="9.99"></label>
      <label>Zustand
        <select id="f-condition">
          <option value="1000">Neu</option>
          <option value="2750">Wie neu</option>
          <option value="4000">Sehr gut</option>
          <option value="5000" selected>Gut</option>
          <option value="6000">Akzeptabel</option>
        </select>
      </label>
      <button id="save-csv-btn" type="button" class="primary">eBay-Datei speichern</button>
    </section>
  </main>

  <dialog id="settings-dialog">
    <form method="dialog">
      <h2>Einstellungen</h2>
      <label>Anthropic-API-Schlüssel <input id="s-anthropic" type="password"></label>
      <label>imgbb-API-Schlüssel <input id="s-imgbb" type="password"></label>
      <label>KI-Modell
        <select id="s-model">
          <option value="claude-sonnet-4-6">Sonnet (günstig)</option>
          <option value="claude-opus-4-8">Opus (stärker)</option>
        </select>
      </label>
      <label>Standort <input id="s-location" value="Berlin"></label>
      <label>Versandkosten <input id="s-shipping_cost" value="5.49"></label>
      <menu>
        <button id="s-save" value="save">Speichern</button>
        <button value="cancel">Abbrechen</button>
      </menu>
    </form>
  </dialog>

  <script src="/static/app.js"></script>
</body>
</html>
```

- [ ] **Step 2: static/style.css anlegen**

```css
:root { font-family: system-ui, sans-serif; font-size: 18px; }
body { margin: 0; background: #f6f5f1; color: #222; }
header { display: flex; justify-content: space-between; align-items: center;
  padding: 1rem 1.5rem; background: #fff; border-bottom: 1px solid #e3e0d8; }
h1 { font-size: 1.3rem; margin: 0; }
main { max-width: 720px; margin: 0 auto; padding: 1.5rem; }
.drop-zone { border: 2px dashed #b9b3a5; border-radius: 12px; padding: 2rem;
  text-align: center; background: #fff; }
.drop-zone.drag { border-color: #c4623a; background: #fff8f4; }
.thumbs { display: flex; flex-wrap: wrap; gap: .5rem; margin-top: 1rem; }
.thumbs img { width: 80px; height: 80px; object-fit: cover; border-radius: 8px; }
button { font-size: 1rem; padding: .6rem 1.1rem; border-radius: 8px;
  border: 1px solid #c9c3b5; background: #fff; cursor: pointer; }
button.primary { background: #c4623a; color: #fff; border: none; }
button:disabled { opacity: .5; cursor: not-allowed; }
#generate-btn { width: 100%; margin: 1rem 0; }
.result { display: flex; flex-direction: column; gap: .8rem; background: #fff;
  padding: 1.5rem; border-radius: 12px; margin-top: 1rem; }
.result label { display: flex; flex-direction: column; gap: .3rem; font-size: .9rem; }
.result input, .result textarea, .result select { font-size: 1rem; padding: .5rem;
  border: 1px solid #c9c3b5; border-radius: 6px; }
.status { min-height: 1.4rem; color: #c4623a; }
dialog { border: none; border-radius: 12px; padding: 1.5rem; min-width: 320px; }
dialog label { display: flex; flex-direction: column; gap: .3rem; margin-bottom: .8rem; }
```

- [ ] **Step 3: static/app.js anlegen**

```javascript
let selectedFiles = [];

const $ = (id) => document.getElementById(id);
const status = (msg) => { $("status").textContent = msg; };

function renderThumbs() {
  const box = $("thumbs");
  box.innerHTML = "";
  selectedFiles.forEach((file) => {
    const img = document.createElement("img");
    img.src = URL.createObjectURL(file);
    box.appendChild(img);
  });
  $("generate-btn").disabled = selectedFiles.length === 0;
}

function addFiles(fileList) {
  for (const f of fileList) if (f.type.startsWith("image/")) selectedFiles.push(f);
  renderThumbs();
}

// Drag & Drop
const dz = $("drop-zone");
dz.addEventListener("dragover", (e) => { e.preventDefault(); dz.classList.add("drag"); });
dz.addEventListener("dragleave", () => dz.classList.remove("drag"));
dz.addEventListener("drop", (e) => {
  e.preventDefault(); dz.classList.remove("drag"); addFiles(e.dataTransfer.files);
});
$("choose-btn").addEventListener("click", () => $("file-input").click());
$("file-input").addEventListener("change", (e) => addFiles(e.target.files));

// Anzeige erstellen
$("generate-btn").addEventListener("click", async () => {
  status("KI analysiert die Fotos …");
  const fd = new FormData();
  selectedFiles.forEach((f) => fd.append("images", f));
  const r = await fetch("/api/generate", { method: "POST", body: fd });
  const data = await r.json();
  if (!r.ok) { status(data.error || "Fehler bei der Analyse."); return; }
  for (const key of ["title", "author", "book_title", "language", "publisher",
                     "publication_year", "book_format", "description"]) {
    $("f-" + key).value = data[key] || "";
  }
  $("result").hidden = false;
  status("Fertig – bitte prüfen und bei Bedarf bearbeiten.");
});

// eBay-Datei speichern
$("save-csv-btn").addEventListener("click", async () => {
  status("Fotos werden hochgeladen und Datei erstellt …");
  const fd = new FormData();
  selectedFiles.forEach((f) => fd.append("images", f));
  for (const key of ["title", "author", "book_title", "language", "publisher",
                     "publication_year", "book_format", "description"]) {
    fd.append(key, $("f-" + key).value);
  }
  fd.append("price", $("f-price").value);
  fd.append("condition_id", $("f-condition").value);
  const r = await fetch("/api/create-csv", { method: "POST", body: fd });
  if (!r.ok) { const e = await r.json(); status(e.error || "Fehler."); return; }
  const blob = await r.blob();
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "ebay-anzeige.csv";
  a.click();
  status("eBay-Datei gespeichert. Jetzt im eBay-CSV-Manager hochladen.");
});

// Einstellungen
const dlg = $("settings-dialog");
$("settings-btn").addEventListener("click", async () => {
  const s = await (await fetch("/api/settings")).json();
  $("s-anthropic").value = s.anthropic_api_key || "";
  $("s-imgbb").value = s.imgbb_api_key || "";
  $("s-model").value = s.model;
  $("s-location").value = s.location;
  $("s-shipping_cost").value = s.shipping_cost;
  dlg.showModal();
});
$("s-save").addEventListener("click", async (e) => {
  e.preventDefault();
  await fetch("/api/settings", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      anthropic_api_key: $("s-anthropic").value,
      imgbb_api_key: $("s-imgbb").value,
      model: $("s-model").value,
      location: $("s-location").value,
      shipping_cost: $("s-shipping_cost").value,
    }),
  });
  dlg.close();
  status("Einstellungen gespeichert.");
});
```

- [ ] **Step 4: App starten und im Browser prüfen**

Run: `. .venv/bin/activate && python app.py`
Expected: Browser öffnet `http://127.0.0.1:5000`, die Seite lädt, Einstellungen-Dialog öffnet sich.

- [ ] **Step 5: Commit**

```bash
git add templates/index.html static/style.css static/app.js
git commit -m "feat: Oberfläche mit Drag&Drop, Vorschau und Export"
```

---

## Task 7: README + .gitignore

**Files:**
- Create: `README.md`
- Create: `.gitignore`

- [ ] **Step 1: .gitignore anlegen**

```
.venv/
__pycache__/
config.json
*.pyc
```

> `config.json` enthält die API-Schlüssel → nicht einchecken.

- [ ] **Step 2: README.md anlegen**

```markdown
# Buch-Anzeigen-Helfer (Etappe 1)

Erzeugt aus Buchfotos per Claude einen eBay-Anzeigentext und eine fertige
eBay-File-Exchange-CSV (Fotos über imgbb gehostet).

## Start (Entwicklung, Mac/Linux)
1. `python3 -m venv .venv && . .venv/bin/activate`
2. `pip install -r requirements.txt`
3. `python app.py` (öffnet den Browser auf http://127.0.0.1:5000)
4. Oben „Einstellungen" → Anthropic- und imgbb-Schlüssel eintragen.

## Ablauf
Fotos eines Buches reinziehen → „Anzeige erstellen" → Felder prüfen/bearbeiten,
Preis und Zustand setzen → „eBay-Datei speichern" → die CSV im eBay-CSV-Manager hochladen.

## Tests
`pytest -q`
```

- [ ] **Step 3: Volltest**

Run: `. .venv/bin/activate && pytest -q`
Expected: Alle Tests grün.

- [ ] **Step 4: Commit**

```bash
git add README.md .gitignore
git commit -m "docs: README und .gitignore"
```

---

## Task 8: Manueller End-to-End-Test (mit echten Schlüsseln)

> Kein automatisierter Test – manuelle Bestätigung des Gesamtflusses. Nutzer-Mitwirkung nötig (Schlüssel, eBay-Konto).

- [ ] **Step 1:** Anthropic- und imgbb-Schlüssel in den Einstellungen eintragen.
- [ ] **Step 2:** 2–3 Fotos eines echten Buches reinziehen → „Anzeige erstellen".
  Erwartet: Felder werden sinnvoll befüllt (Titel ≤80 Zeichen, Beschreibung auf Deutsch).
- [ ] **Step 3:** Preis hoch setzen (z. B. 999.99) und Zustand wählen → „eBay-Datei speichern".
  Erwartet: `ebay-anzeige.csv` wird heruntergeladen.
- [ ] **Step 4:** CSV im eBay-CSV-Manager hochladen (privates Test-Konto).
  Erwartet: Ergebnisbericht `Status = Warning/Success` mit `ItemID` (wie im Machbarkeitstest).
- [ ] **Step 5:** Test-Anzeige unter „Aktive Anzeigen" wieder beenden.
- [ ] **Step 6:** Bei Fehlern im Bericht: Feld anpassen (vgl. Spec Abschnitt 11) und erneut.

---

## Offene Punkte für später (nicht Teil von Etappe 1)
- Windows-Verpackung (Doppelklick-Start) – braucht am Schluss einen Windows-Rechner.
- Genauen Prompt des Vaters in die Einstellungen übernehmen (ersetzt `DEFAULT_PROMPT`).
- Feindesign nach ui-ux-pro-max.
- Optionale Kopier-Knöpfe pro Feld (in Spec als „falls gewünscht" genannt; in Etappe 1 weggelassen).
