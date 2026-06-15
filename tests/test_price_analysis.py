# tests/test_price_analysis.py
from unittest.mock import patch
from price_analysis import analyze_price, PriceAnalysis

def test_analyze_price_validiert_und_reicht_modell_durch():
    fake = {
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
    assert result.comparables[0].source == "Booklooker"
    assert result.comparables[0].price == "12.00"
    assert m.call_args.kwargs["model"] == "claude-opus-4-8"

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
