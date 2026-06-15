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
