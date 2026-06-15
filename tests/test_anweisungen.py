from anweisungen import parse, render, load, save, ensure

# (key, label) wie in config.PROMPT_FIELDS, hier verkürzt für die Tests.
FIELDS = [("title", "Titel"), ("author", "Autor"), ("description", "Beschreibung")]

def test_render_parse_roundtrip():
    general = "Allgemeiner Text\nmit zwei Zeilen."
    fields = {"title": "Titelregel", "author": "Autorregel", "description": "<p>HTML</p>"}
    text = render(general, fields, "Beispiel.", FIELDS)
    back = parse(text, FIELDS)
    assert back["prompt_general"] == general
    assert back["prompt_fields"] == fields
    assert back["prompt_examples"] == "Beispiel."

def test_render_enthaelt_ueberschriften():
    text = render("g", {"title": "t"}, "", FIELDS)
    assert "# Allgemeine Regeln #" in text
    assert "# Titel #" in text
    assert "# Beispiel-Beschreibung #" in text

def test_parse_nur_vorhandene_abschnitte():
    back = parse("# Titel #\nNur der Titel.", FIELDS)
    assert back == {"prompt_fields": {"title": "Nur der Titel."}}
    assert "prompt_general" not in back

def test_parse_ignoriert_unbekannte_ueberschrift():
    back = parse("# Quatsch #\negal\n# Autor #\nAutorregel", FIELDS)
    assert back["prompt_fields"] == {"author": "Autorregel"}

def test_parse_tolerante_raute_schreibweisen():
    for headline in ("# Titel #", "#Titel#", "# Titel#", "  #  Titel  #  "):
        back = parse(headline + "\nInhalt", FIELDS)
        assert back["prompt_fields"]["title"] == "Inhalt", headline

def test_save_und_load_neben_config(tmp_path):
    cfg = str(tmp_path / "config.json")
    save("g", {"title": "t", "author": "a", "description": "d"}, "ex", FIELDS, cfg)
    assert (tmp_path / "anweisungen.txt").exists()
    back = load(cfg, FIELDS)
    assert back["prompt_general"] == "g"
    assert back["prompt_fields"]["title"] == "t"
    assert back["prompt_examples"] == "ex"

def test_load_ohne_datei_gibt_none(tmp_path):
    assert load(str(tmp_path / "config.json"), FIELDS) is None

def test_ensure_legt_nur_einmal_an(tmp_path):
    cfg = str(tmp_path / "config.json")
    ensure("g1", {"title": "t1"}, "", FIELDS, cfg)
    ensure("g2", {"title": "t2"}, "", FIELDS, cfg)  # darf NICHT überschreiben
    assert load(cfg, FIELDS)["prompt_general"] == "g1"
