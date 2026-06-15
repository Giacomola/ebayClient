# tests/test_price_analysis.py
from unittest.mock import patch
from price_analysis import analyze_price, PriceAnalysis

def test_analyze_price_validiert_und_reicht_modell_durch():
    fake = {
        "comparables": [
            {"title": "Der Hobbit 1957", "price": "12.00",
             "url": "https://www.booklooker.de/x", "source": "Booklooker"},
        ],
        "recommended_price": "11.50",
        "price_reason": "Gut erhaltene Ausgabe, Angebote 10–14 €.",
        "note": "Wenige Vergleichsangebote gefunden.",
    }
    with patch("price_analysis.complete_json", return_value=fake) as m:
        result = analyze_price(api_key="sk", model="claude-opus-4-8",
                               author="J.R.R. Tolkien", book_title="Der Hobbit",
                               title="T", language="Deutsch",
                               publication_year="1957", publisher="", book_format="",
                               condition="Gut")
    assert isinstance(result, PriceAnalysis)
    assert result.comparables[0].source == "Booklooker"
    assert result.comparables[0].price == "12.00"
    assert result.recommended_price == "11.50"
    assert result.price_reason.startswith("Gut erhalten")
    assert m.call_args.kwargs["model"] == "claude-opus-4-8"
    # Der Zustand muss im Suchauftrag an die KI auftauchen.
    assert "Gut" in m.call_args.kwargs["content"][0]["text"]

def test_recommended_price_null_wird_leerstring():
    pa = PriceAnalysis(recommended_price=None, price_reason=None)
    assert pa.recommended_price == "" and pa.price_reason == ""

def test_priceanalysis_hat_defaults():
    pa = PriceAnalysis()
    assert pa.comparables == []
    assert pa.note == ""

def test_priceanalysis_null_wird_zu_leerstring():
    # Die KI liefert null, wenn sie nichts findet – das darf nicht abstürzen.
    pa = PriceAnalysis(note=None,
                       comparables=[{"title": "X", "price": None, "url": None,
                                     "source": None}])
    assert pa.note == ""
    assert pa.comparables[0].price == ""
    assert pa.comparables[0].url == ""

def test_priceanalysis_zahl_wird_zu_text():
    # Manchmal kommt eine Zahl statt Text – sauber in Text umwandeln.
    pa = PriceAnalysis(comparables=[{"title": "X", "price": 12}])
    assert pa.comparables[0].price == "12"
