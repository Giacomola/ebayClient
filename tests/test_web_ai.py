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

def test_complete_json_bricht_nach_zu_vielen_runden_ab():
    import pytest
    paused = SimpleNamespace(stop_reason="pause_turn", content=[_text_block("…suche…")])
    fake_client = MagicMock()
    fake_client.messages.create.return_value = paused
    with patch("web_ai.anthropic.Anthropic", return_value=fake_client):
        with pytest.raises(RuntimeError):
            complete_json(api_key="sk", model="claude-opus-4-8",
                          content=[{"type": "text", "text": "P"}])

def test_extract_json_toleriert_trailing_comma_objekt():
    from web_ai import _extract_json
    assert _extract_json('Antwort: {"a": 1, "b": "x", } – fertig') == {"a": 1, "b": "x"}

def test_extract_json_toleriert_trailing_comma_liste():
    from web_ai import _extract_json
    assert _extract_json('{"xs": [1, 2, 3, ], "y": 4}') == {"xs": [1, 2, 3], "y": 4}

def test_extract_json_repariert_aber_laesst_string_kommas_in_ruhe():
    # Komma+Klammer INNERHALB einer Zeichenkette darf NICHT entfernt werden,
    # nur das echte überzählige Komma vor der schließenden Klammer.
    from web_ai import _extract_json
    assert _extract_json('{"t": "Preis, } ok", "n": 2, }') == {"t": "Preis, } ok", "n": 2}

def test_extract_json_unreparierbar_meldet_klaren_fehler():
    import pytest
    from web_ai import _extract_json
    with pytest.raises(ValueError):
        _extract_json('{"a": 1 "b": 2}')  # fehlendes Komma – nicht reparierbar
