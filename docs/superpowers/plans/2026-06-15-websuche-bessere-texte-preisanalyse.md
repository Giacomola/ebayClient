# Websuche, bessere Texte & Preisanalyse – Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Der Buch-Anzeigen-Helfer ergänzt fehlende Buchdaten per Websuche, schreibt verkaufsstärkere Texte (Standardmodell Opus 4.8) und liefert eine Preisempfehlung mit Quellen – für den Vater weiterhin ein Knopf.

**Architecture:** Variante A – zwei fokussierte Such-Aufrufe. Ein neues Hilfsmodul `web_ai.py` kapselt den Websuche-Aufruf (inkl. `pause_turn`-Schleife) und gibt geparstes JSON zurück. `ai_client.analyze_book` (Text) und das neue `price_analysis.analyze_price` (Preis) bauen darauf auf. `app.py` bekommt eine zweite Route `/api/price`; die Oberfläche ruft erst `/api/generate`, dann `/api/price` auf.

**Tech Stack:** Python 3.14, Flask, anthropic 0.107.1 (server-seitiges Websuche-Werkzeug), pydantic 2, pytest. Frontend: HTML/CSS/Vanilla-JS.

**Wichtige Technik-Entscheidung (aus Spec 6.3):** Erzwungenes JSON-Ausgabeformat (`output_config.format`) ist mit dem Websuche-Werkzeug nicht zuverlässig kompatibel (Websuche liefert Citations; Structured Outputs lehnt Citations ab → 400). Deshalb verwenden wir den robusten Weg: Die KI wird per Prompt angewiesen, **ausschließlich ein JSON-Objekt** zurückzugeben, das der Code mit `json.loads` einliest und in ein pydantic-Modell validiert.

---

## File Structure

```
ebay-client/
  web_ai.py            # NEU: Websuche-Aufruf + pause_turn-Schleife + JSON-Extraktion  [TDD]
  ai_client.py         # GEÄNDERT: BookFields erweitert, Websuche, JSON-Vertrag
  price_analysis.py    # NEU: analyze_price -> PriceAnalysis (Spanne + Vergleiche)     [TDD]
  config.py            # GEÄNDERT: Standardmodell Opus 4.8, Verkaufston im Prompt
  app.py               # GEÄNDERT: /api/generate (erweitert) + neue Route /api/price
  templates/index.html # GEÄNDERT: Web-Abzeichen, Quellen, Preisempfehlung
  static/app.js        # GEÄNDERT: zweistufiger Ablauf, Render-Funktionen
  static/style.css     # GEÄNDERT: Stile für Abzeichen/Quellen/Preis
  tests/test_web_ai.py        # NEU
  tests/test_price_analysis.py# NEU
  tests/test_ai_client.py     # GEÄNDERT
  tests/test_app.py           # GEÄNDERT
```

`web_ai.py` ist das gemeinsame, einzeln testbare Herzstück; `ai_client` und `price_analysis` bauen darauf auf und validieren je in ihr eigenes pydantic-Modell.

---

## Task 1: web_ai.py – gemeinsamer Websuche-Aufruf

**Files:**
- Create: `web_ai.py`
- Test: `tests/test_web_ai.py`

- [ ] **Step 1: Failing Tests schreiben**

```python
# tests/test_web_ai.py
from types import SimpleNamespace
from unittest.mock import patch, MagicMock
from web_ai import complete_json, WEB_SEARCH_TOOL

def _text_block(text):
    return SimpleNamespace(type="text", text=text)

def test_complete_json_parst_und_schickt_websuche_werkzeug():
    resp = SimpleNamespace(stop_reason="end_turn",
                           content=[_text_block('Hier: {"a": 1, "b": "x"} fertig')])
    fake_client = MagicMock()
    fake_client.messages.create.return_value = resp
    with patch("web_ai.anthropic.Anthropic", return_value=fake_client):
        data = complete_json(api_key="sk", model="claude-opus-4-8",
                             content=[{"type": "text", "text": "P"}])
    assert data == {"a": 1, "b": "x"}
    # Websuche-Werkzeug wurde mitgeschickt
    assert WEB_SEARCH_TOOL in fake_client.messages.create.call_args.kwargs["tools"]
    assert fake_client.messages.create.call_args.kwargs["model"] == "claude-opus-4-8"

def test_complete_json_setzt_pause_turn_fort():
    paused = SimpleNamespace(stop_reason="pause_turn", content=[_text_block("…suche…")])
    done = SimpleNamespace(stop_reason="end_turn", content=[_text_block('{"ok": true}')])
    fake_client = MagicMock()
    fake_client.messages.create.side_effect = [paused, done]
    with patch("web_ai.anthropic.Anthropic", return_value=fake_client):
        data = complete_json(api_key="sk", model="claude-opus-4-8",
                             content=[{"type": "text", "text": "P"}])
    assert data == {"ok": True}
    assert fake_client.messages.create.call_count == 2
```

- [ ] **Step 2: Tests laufen lassen (müssen fehlschlagen)**

Run: `. .venv/bin/activate && pytest tests/test_web_ai.py -v`
Expected: FAIL (`ModuleNotFoundError: web_ai`).

- [ ] **Step 3: web_ai.py implementieren**

```python
# web_ai.py
"""Gemeinsamer Helfer: schickt einen Auftrag mit aktiver Websuche an Claude und
gibt das zurückgegebene JSON-Objekt als dict zurück.

Das server-seitige Websuche-Werkzeug kann die Antwort mit stop_reason "pause_turn"
unterbrechen; dann wird der Aufruf fortgesetzt, bis die KI fertig ist."""
import json
import anthropic

# Websuche-Werkzeug. Hinweis: Sollte die API diese Version ablehnen, auf
# {"type": "web_search_20250305", "name": "web_search"} ausweichen (beim Bauen prüfen).
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search"}

def _extract_json(text: str) -> dict:
    """Holt das erste JSON-Objekt aus dem Antworttext (von erster { bis letzter })."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("Die KI hat keine verwertbare JSON-Antwort geliefert.")
    return json.loads(text[start:end + 1])

def complete_json(*, api_key: str, model: str, content: list, max_tokens: int = 4000) -> dict:
    client = anthropic.Anthropic(api_key=api_key, max_retries=4, timeout=180.0)
    messages = [{"role": "user", "content": content}]
    resp = None
    for _ in range(6):  # genug Runden für mehrere Websuchen, aber endlich
        resp = client.messages.create(
            model=model, max_tokens=max_tokens,
            tools=[WEB_SEARCH_TOOL], messages=messages,
        )
        if resp.stop_reason == "pause_turn":
            messages.append({"role": "assistant", "content": resp.content})
            continue
        break
    text = "".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    return _extract_json(text)
```

- [ ] **Step 4: Tests laufen lassen (müssen bestehen)**

Run: `. .venv/bin/activate && pytest tests/test_web_ai.py -v`
Expected: PASS (2 Tests).

- [ ] **Step 5: Commit**

```bash
git add web_ai.py tests/test_web_ai.py
git commit -m "feat: web_ai – Websuche-Aufruf mit JSON-Antwort und pause_turn-Schleife"
```

---

## Task 2: ai_client.py – Websuche + erweiterte Felder

**Files:**
- Modify: `ai_client.py`
- Test: `tests/test_ai_client.py`

- [ ] **Step 1: Tests anpassen (failing)**

Ersetze den kompletten Inhalt von `tests/test_ai_client.py`:

```python
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
```

- [ ] **Step 2: Tests laufen lassen (müssen fehlschlagen)**

Run: `. .venv/bin/activate && pytest tests/test_ai_client.py -v`
Expected: FAIL (`ImportError` / `complete_json` nicht patchbar bzw. neue Felder fehlen).

- [ ] **Step 3: ai_client.py neu schreiben**

Ersetze den kompletten Inhalt von `ai_client.py`:

```python
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
```

- [ ] **Step 4: Tests laufen lassen (müssen bestehen)**

Run: `. .venv/bin/activate && pytest tests/test_ai_client.py -v`
Expected: PASS (3 Tests).

- [ ] **Step 5: Commit**

```bash
git add ai_client.py tests/test_ai_client.py
git commit -m "feat: ai_client mit Websuche, Quellen und Web-Markierung der Felder"
```

---

## Task 3: price_analysis.py – Preisempfehlung

**Files:**
- Create: `price_analysis.py`
- Test: `tests/test_price_analysis.py`

- [ ] **Step 1: Failing Test schreiben**

```python
# tests/test_price_analysis.py
from unittest.mock import patch
from price_analysis import analyze_price, PriceAnalysis

def test_analyze_price_validiert_und_reicht_modell_durch():
    fake = {
        "price_low": "8.00", "price_high": "15.00", "currency": "EUR",
        "comparables": [
            {"title": "Der Hobbit 1957", "price": "12.00",
             "url": "https://www.booklooker.de/x", "source": "Booklooker"},
        ],
        "note": "Wenige Vergleichsangebote gefunden.",
    }
    with patch("price_analysis.complete_json", return_value=fake) as m:
        result = analyze_price(api_key="sk", model="claude-opus-4-8",
                               author="J.R.R. Tolkien", book_title="Der Hobbit",
                               title="T", language="Deutsch",
                               publication_year="1957", publisher="", book_format="")
    assert isinstance(result, PriceAnalysis)
    assert result.price_low == "8.00"
    assert result.comparables[0].source == "Booklooker"
    assert m.call_args.kwargs["model"] == "claude-opus-4-8"

def test_priceanalysis_hat_defaults():
    pa = PriceAnalysis()
    assert pa.currency == "EUR"
    assert pa.comparables == []
```

- [ ] **Step 2: Test laufen lassen (muss fehlschlagen)**

Run: `. .venv/bin/activate && pytest tests/test_price_analysis.py -v`
Expected: FAIL (`ModuleNotFoundError: price_analysis`).

- [ ] **Step 3: price_analysis.py implementieren**

```python
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
```

- [ ] **Step 4: Test laufen lassen (muss bestehen)**

Run: `. .venv/bin/activate && pytest tests/test_price_analysis.py -v`
Expected: PASS (2 Tests).

- [ ] **Step 5: Commit**

```bash
git add price_analysis.py tests/test_price_analysis.py
git commit -m "feat: price_analysis – Preisspanne und Vergleichsangebote per Websuche"
```

---

## Task 4: config.py – Standardmodell Opus 4.8 + Verkaufston

**Files:**
- Modify: `config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Failing Test ergänzen**

Hänge ans Ende von `tests/test_config.py` an (oder erstelle die Datei mit diesem Inhalt, falls sie fehlt):

```python
from config import load_settings, DEFAULTS, build_system_prompt

def test_standardmodell_ist_opus(tmp_path):
    settings = load_settings(str(tmp_path / "config.json"))
    assert settings["model"] == "claude-opus-4-8"

def test_general_prompt_nennt_verkauf_und_websuche():
    text = DEFAULTS["prompt_general"].lower()
    assert "websuche" in text
    assert "käufer" in text or "verkauf" in text
```

- [ ] **Step 2: Test laufen lassen (muss fehlschlagen)**

Run: `. .venv/bin/activate && pytest tests/test_config.py -v`
Expected: FAIL (`model` ist noch `claude-sonnet-4-6`; Prompt enthält die Wörter noch nicht).

- [ ] **Step 3: config.py anpassen**

In `config.py` den `DEFAULT_PROMPT_GENERAL` ersetzen durch:

```python
DEFAULT_PROMPT_GENERAL = (
    "Du bist ein Assistent für den Verkauf antiquarischer und gebrauchter Bücher auf "
    "eBay.de. Analysiere die Fotos EINES Buches (Einband, Buchrücken, Titelseite, "
    "Impressum, ggf. Inhaltsverzeichnis) und fülle die Anzeigenfelder aus. Nutze die "
    "Websuche, um die exakte Ausgabe zu bestimmen und fehlende Angaben zu ergänzen. "
    "Schreibe auf Deutsch: antiquarisch korrekt UND als ansprechender Verkaufstext, der "
    "einen möglichen Käufer überzeugt – sachlich, aber einladend, ohne Übertreibung oder "
    "erfundene Angaben. Gib bevorzugt an, was auf den Fotos sicher erkennbar ist; aus dem "
    "Netz ergänzte Angaben sind erlaubt, müssen aber belegbar sein. "
    "Verwende niemals Semikolons. Formatiere die Beschreibung als eBay-taugliches HTML: "
    "Absätze mit <p>…</p>, Zeilenumbrüche mit <br>, Hervorhebungen mit <b>…</b>; verwende "
    "KEINE echten Zeilenumbrüche (Enter-Taste), sondern ausschließlich diese HTML-Tags."
)
```

In `config.py` im `DEFAULTS`-Wörterbuch die Modellzeile ändern:

```python
    "model": "claude-opus-4-8",
```

- [ ] **Step 4: Test laufen lassen (muss bestehen)**

Run: `. .venv/bin/activate && pytest tests/test_config.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add config.py tests/test_config.py
git commit -m "feat: Standardmodell Opus 4.8 und Verkaufston/Websuche im Prompt"
```

---

## Task 5: app.py – /api/generate erweitert + neue Route /api/price

**Files:**
- Modify: `app.py`
- Test: `tests/test_app.py`

- [ ] **Step 1: Failing Tests ergänzen**

Hänge ans Ende von `tests/test_app.py` an:

```python
from price_analysis import PriceAnalysis

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
```

- [ ] **Step 2: Tests laufen lassen (müssen fehlschlagen)**

Run: `. .venv/bin/activate && pytest tests/test_app.py -v`
Expected: FAIL (`/api/price` gibt es noch nicht; ggf. `analyze_price` nicht importiert).

- [ ] **Step 3: app.py anpassen**

In `app.py` den Import ergänzen (direkt nach `from ai_client import analyze_book`):

```python
from price_analysis import analyze_price
```

In `app.py` die Funktion `generate()` so anpassen, dass die erweiterten Felder zurückkommen (die letzte Zeile von `generate()` ist bereits `return jsonify(book.model_dump())` – `model_dump()` enthält die neuen Felder automatisch, hier ist also **keine Änderung nötig**). Füge **nach** der `generate()`-Route (vor `@app.post("/api/choose-folder")`) die neue Route ein:

```python
    @app.post("/api/price")
    def price():
        settings = load_settings(config_path)
        if not settings["anthropic_api_key"]:
            return jsonify({"error": "Kein Anthropic-API-Schlüssel hinterlegt. "
                                     "Bitte in den Einstellungen eintragen."}), 400
        data = request.get_json(force=True) or {}
        try:
            result = analyze_price(
                api_key=settings["anthropic_api_key"], model=settings["model"],
                author=data.get("author", ""), book_title=data.get("book_title", ""),
                title=data.get("title", ""), language=data.get("language", ""),
                publication_year=data.get("publication_year", ""),
                publisher=data.get("publisher", ""), book_format=data.get("book_format", ""))
        except anthropic.AuthenticationError:
            return jsonify({"error": "Der Anthropic-API-Schlüssel fehlt oder ist "
                                     "ungültig."}), 401
        except anthropic.APIConnectionError:
            return jsonify({"error": "Keine Verbindung zu den KI-Servern. Bitte die "
                                     "Internetverbindung prüfen."}), 503
        except anthropic.APIStatusError as e:
            if e.status_code >= 500:
                return jsonify({"error": "Die KI-Server sind gerade überlastet. Bitte "
                                         "kurz warten und erneut versuchen."}), 503
            return jsonify({"error": f"KI-Fehler ({e.status_code}): {e.message}"}), 502
        except Exception as e:  # noqa: BLE001 - dem Nutzer verständlich melden
            return jsonify({"error": f"Preis-Recherche fehlgeschlagen: {e}"}), 502
        return jsonify(result.model_dump())
```

- [ ] **Step 4: Tests laufen lassen (müssen bestehen)**

Run: `. .venv/bin/activate && pytest tests/test_app.py -v`
Expected: PASS (alle, inkl. der drei neuen).

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_app.py
git commit -m "feat: /api/price-Route und erweiterte Felder aus /api/generate"
```

---

## Task 6: Oberfläche – Abzeichen, Quellen, Preisempfehlung, zweistufiger Ablauf

**Files:**
- Modify: `templates/index.html`
- Modify: `static/style.css`
- Modify: `static/app.js`

- [ ] **Step 1: index.html – Web-Abzeichen an den Feld-Labels**

Ersetze im `<section id="result" ...>` die sieben Feld-Labels (Titel bis Format) und das Beschreibungs-Label durch diese Fassung (jeweils mit verstecktem Abzeichen):

```html
      <label>Titel <span class="web-badge" data-key="title" hidden>🌐 aus Websuche</span> <input id="f-title" maxlength="80"></label>
      <label>Autor <span class="web-badge" data-key="author" hidden>🌐 aus Websuche</span> <input id="f-author"></label>
      <label>Buchtitel <span class="web-badge" data-key="book_title" hidden>🌐 aus Websuche</span> <input id="f-book_title"></label>
      <label>Sprache <span class="web-badge" data-key="language" hidden>🌐 aus Websuche</span> <input id="f-language"></label>
      <label>Verlag <span class="web-badge" data-key="publisher" hidden>🌐 aus Websuche</span> <input id="f-publisher"></label>
      <label>Erscheinungsjahr <span class="web-badge" data-key="publication_year" hidden>🌐 aus Websuche</span> <input id="f-publication_year"></label>
      <label>Format <span class="web-badge" data-key="book_format" hidden>🌐 aus Websuche</span> <input id="f-book_format"></label>
      <label>Beschreibung <span class="web-badge" data-key="description" hidden>🌐 aus Websuche</span> <span class="sub">(so erscheint sie ungefähr bei eBay – direkt bearbeitbar)</span>
        <div id="f-description" class="rich" contenteditable="true"></div>
      </label>
```

- [ ] **Step 2: index.html – Abschnitte Quellen und Preisempfehlung**

Füge **direkt nach** dem Beschreibungs-Label (vor `<label>Preis …`) die Quellen ein:

```html
      <section id="sources-box" class="info-box" hidden>
        <h3>Quellen</h3>
        <ul id="sources-list"></ul>
      </section>
```

Füge **direkt nach** dem Zustand-`<label>` (vor `<div class="save-area">`) die Preisempfehlung ein:

```html
      <section id="price-box" class="info-box" hidden>
        <h3>Preisempfehlung</h3>
        <p id="price-range"></p>
        <ul id="price-comparables"></ul>
        <p id="price-note" class="sub"></p>
        <button id="price-apply" type="button">in Preisfeld übernehmen</button>
      </section>
```

- [ ] **Step 3: style.css – Stile ergänzen**

Hänge ans Ende von `static/style.css` an:

```css
.web-badge { font-weight: normal; color: #2b6a4b; font-size: .75rem;
  background: #e7f3ec; padding: .05rem .35rem; border-radius: 4px; }
.info-box { background: #faf9f6; border: 1px solid #e3e0d8; border-radius: 8px;
  padding: .8rem 1rem; }
.info-box h3 { margin: 0 0 .5rem; font-size: 1rem; }
.info-box ul { margin: 0; padding-left: 1.2rem; }
.info-box li { margin-bottom: .3rem; }
#price-range { font-size: 1.1rem; font-weight: 600; margin: 0 0 .5rem; }
#price-apply { margin-top: .6rem; }
```

- [ ] **Step 4: app.js – Render-Funktionen und zweistufiger Ablauf**

In `static/app.js` direkt nach der Zeile `const status = (msg) => { ... };` (etwa Zeile 4) diese Helfer einfügen:

```javascript
// Zeigt die 🌐-Abzeichen nur an den Feldern, die aus der Websuche stammen.
function applyBadges(keys) {
  document.querySelectorAll(".web-badge").forEach((b) => {
    b.hidden = !keys.includes(b.dataset.key);
  });
}
// Listet die Quellen als anklickbare Links.
function renderSources(sources) {
  const box = $("sources-box");
  const list = $("sources-list");
  list.innerHTML = "";
  for (const s of sources || []) {
    if (!s.url) continue;
    const li = document.createElement("li");
    const a = document.createElement("a");
    a.href = s.url; a.target = "_blank"; a.rel = "noopener";
    a.textContent = s.title || s.url;
    li.appendChild(a);
    list.appendChild(li);
  }
  box.hidden = list.children.length === 0;
}
// Zeigt Preisspanne, Vergleichsangebote und Hinweis.
function renderPrice(d) {
  $("price-box").hidden = false;
  if (d.price_low || d.price_high) {
    $("price-range").textContent = `ca. ${d.price_low} – ${d.price_high} ${d.currency || "EUR"}`;
  } else {
    $("price-range").textContent = "Keine Preise gefunden.";
  }
  const list = $("price-comparables");
  list.innerHTML = "";
  for (const c of d.comparables || []) {
    const li = document.createElement("li");
    if (c.url) {
      const a = document.createElement("a");
      a.href = c.url; a.target = "_blank"; a.rel = "noopener";
      a.textContent = `${c.title || c.source} – ${c.price}`;
      li.appendChild(a);
    } else {
      li.textContent = `${c.title || c.source} – ${c.price}`;
    }
    list.appendChild(li);
  }
  $("price-note").textContent = d.note || "";
}
// Holt die Preisempfehlung anhand der aktuellen Feldwerte.
async function fetchPrice() {
  $("price-box").hidden = false;
  $("price-range").textContent = "💶 prüfe Preise …";
  $("price-comparables").innerHTML = "";
  $("price-note").textContent = "";
  const body = {};
  for (const key of ["title", "author", "book_title", "language",
                     "publication_year", "publisher", "book_format"]) {
    body[key] = $("f-" + key).value;
  }
  let r, d;
  try {
    r = await fetch("/api/price", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    d = await r.json();
  } catch (e) {
    $("price-range").textContent = "Preisprüfung nicht möglich.";
    return;
  }
  if (!r.ok) { $("price-range").textContent = d.error || "Preise nicht ermittelbar."; return; }
  renderPrice(d);
}
```

In `static/app.js` den `generate-btn`-Klick-Handler ersetzen durch:

```javascript
$("generate-btn").addEventListener("click", async () => {
  status("🔎 recherchiere im Netz … (das kann ~30–60 Sekunden dauern)");
  applyBadges([]);
  renderSources([]);
  $("price-box").hidden = true;
  const fd = new FormData();
  selectedFiles.forEach((f) => fd.append("images", f));
  const r = await fetch("/api/generate", { method: "POST", body: fd });
  const data = await r.json();
  if (!r.ok) { status(data.error || "Fehler bei der Analyse."); return; }
  for (const key of ["title", "author", "book_title", "language", "publisher",
                     "publication_year", "book_format"]) {
    $("f-" + key).value = data[key] || "";
  }
  $("f-description").innerHTML = data.description || "";
  applyBadges(data.web_sourced_fields || []);
  renderSources(data.sources || []);
  $("result").hidden = false;
  status("Text fertig – prüfe jetzt die Preise …");
  saveFieldsNow();
  fetchPrice();  // zweiter Aufruf, füllt die Preisempfehlung
});
```

In `static/app.js` den `price-apply`-Knopf verdrahten – füge nach dem `generate-btn`-Handler ein:

```javascript
// Übernimmt den Mittelwert der Preisspanne ins Preisfeld (manuell, auf Wunsch).
on("price-apply", "click", () => {
  const text = $("price-range").textContent.match(/[\d.,]+/g);
  if (!text || text.length < 2) return;
  const low = parseFloat(text[0].replace(",", "."));
  const high = parseFloat(text[1].replace(",", "."));
  if (isNaN(low) || isNaN(high)) return;
  $("f-price").value = ((low + high) / 2).toFixed(2);
  saveFieldsSoon();
});
```

In `static/app.js` im `new-case-btn`-Handler nach `$("result").hidden = true;` ergänzen:

```javascript
  applyBadges([]);
  renderSources([]);
  $("price-box").hidden = true;
```

- [ ] **Step 5: App starten und im Browser prüfen**

Run: `. .venv/bin/activate && python app.py`
Expected: Browser öffnet `http://127.0.0.1:5050`; mit hinterlegten Schlüsseln und Fotos erscheint nach „Anzeige erstellen" der Text mit 🌐-Abzeichen an ergänzten Feldern, eine Quellen-Liste und kurz darauf die Preisempfehlung. (Ohne echte Schlüssel zumindest: Seite lädt, Knöpfe da, klare Fehlermeldung.)

- [ ] **Step 6: Commit**

```bash
git add templates/index.html static/style.css static/app.js
git commit -m "feat: Oberfläche – Web-Abzeichen, Quellen und Preisempfehlung (zweistufig)"
```

---

## Task 7: Volltest + manueller End-to-End-Test

**Files:** keine (nur Ausführung)

- [ ] **Step 1: Alle automatischen Tests grün**

Run: `. .venv/bin/activate && pytest -q`
Expected: alle Tests bestehen.

- [ ] **Step 2: Websuche-Werkzeug-Version verifizieren (echter Schlüssel)**

Mit hinterlegtem Anthropic-Schlüssel ein echtes Buch durchlaufen lassen. Erwartet: kein 400 wegen unbekanntem Werkzeugtyp. Falls doch, in `web_ai.py` `WEB_SEARCH_TOOL` auf `{"type": "web_search_20250305", "name": "web_search"}` umstellen und Tests erneut laufen lassen.

- [ ] **Step 3: Qualität prüfen**

Erwartet: Text klingt verkaufsorientiert und antiquarisch korrekt; fehlende Felder (z. B. Jahr/Verlag) werden – wo im Netz auffindbar – ergänzt und mit 🌐 markiert; Quellen anklickbar; Preisempfehlung mit Spanne + Vergleichsangeboten (oder ehrlicher „wenig gefunden"-Hinweis).

- [ ] **Step 4: Robustheit prüfen**

Erwartet: Ohne Internet/bei Fehler bleibt der Text erhalten und der Preisbereich zeigt eine verständliche Meldung statt eines Absturzes.

---

## Offene Punkte für später (nicht Teil dieses Plans)
- Preis-Prompt in der „Anweisungen"-Oberfläche bearbeitbar machen (aktuell fester Text in `price_analysis.py`).
- Feinschliff der Prompt-Formulierungen mit dem Nutzer.
- Optional: adaptives Denken (`thinking`) für noch bessere Ausgaben-Bestimmung – bewusst weggelassen für Einfachheit und Kostenkontrolle.
