import json
from config import (load_settings, save_settings, build_system_prompt,
                    DEFAULTS, DEFAULT_FIELD_PROMPTS)

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

def test_defaults_have_structured_prompt():
    assert "prompt_general" in DEFAULTS
    assert set(DEFAULTS["prompt_fields"]) == set(DEFAULT_FIELD_PROMPTS)
    assert "title" in DEFAULTS["prompt_fields"]

def test_legacy_prompt_is_ignored(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"prompt": "alter Text"}), encoding="utf-8")
    loaded = load_settings(str(p))
    assert "prompt" not in loaded
    assert loaded["prompt_fields"]["title"] == DEFAULT_FIELD_PROMPTS["title"]

def test_missing_field_falls_back_to_default(tmp_path):
    p = tmp_path / "config.json"
    p.write_text(json.dumps({"prompt_fields": {"title": "Mein Titel-Stil"}}),
                 encoding="utf-8")
    loaded = load_settings(str(p))
    assert loaded["prompt_fields"]["title"] == "Mein Titel-Stil"
    assert loaded["prompt_fields"]["author"] == DEFAULT_FIELD_PROMPTS["author"]

def test_save_keeps_custom_and_default_fields(tmp_path):
    p = tmp_path / "config.json"
    save_settings({"prompt_fields": {"title": "Kurz halten"}}, str(p))
    loaded = load_settings(str(p))
    assert loaded["prompt_fields"]["title"] == "Kurz halten"
    assert loaded["prompt_fields"]["language"] == DEFAULT_FIELD_PROMPTS["language"]

def test_build_system_prompt_examples_optional():
    settings = load_settings("gibt-es-nicht.json")
    ohne = build_system_prompt(settings)
    assert "Beispiel-Beschreibung" not in ohne          # leer -> kein Abschnitt
    settings["prompt_examples"] = "Mustertext, fett und schön formuliert."
    mit = build_system_prompt(settings)
    assert "Mustertext, fett und schön formuliert." in mit
    assert "NICHT die konkreten Angaben" in mit          # Schutz vor Faktenklau
    assert DEFAULTS["prompt_examples"] == ""

def test_build_system_prompt_includes_general_and_fields():
    settings = load_settings("does-not-exist.json")
    settings["prompt_general"] = "Allgemeiner Hinweis."
    settings["prompt_fields"]["title"] = "Titel-Sonderregel."
    text = build_system_prompt(settings)
    assert "Allgemeiner Hinweis." in text
    assert "Titel-Sonderregel." in text
    assert "title (Titel):" in text
    assert "author (Autor):" in text
