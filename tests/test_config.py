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
    assert loaded["shipping_service"] == "DE_DHLPaket"
