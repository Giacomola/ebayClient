from draft import load_draft, update_fields, update_images, clear_draft, EMPTY

def test_load_missing_returns_empty(tmp_path):
    d = load_draft(str(tmp_path / "draft.json"))
    assert d == EMPTY

def test_update_fields_keeps_images(tmp_path):
    p = str(tmp_path / "draft.json")
    update_images([{"media_type": "image/jpeg", "data_url": "data:..."}], p)
    update_fields({"title": "Mein Buch"}, True, p)
    d = load_draft(p)
    assert d["fields"]["title"] == "Mein Buch"
    assert d["result_visible"] is True
    assert len(d["images"]) == 1          # Fotos bleiben beim Feld-Speichern erhalten

def test_update_images_keeps_fields(tmp_path):
    p = str(tmp_path / "draft.json")
    update_fields({"title": "Mein Buch"}, True, p)
    update_images([{"media_type": "image/png", "data_url": "data:..."}], p)
    d = load_draft(p)
    assert d["fields"]["title"] == "Mein Buch"   # Felder bleiben beim Foto-Speichern erhalten
    assert d["images"][0]["media_type"] == "image/png"

def test_clear_resets_everything(tmp_path):
    p = str(tmp_path / "draft.json")
    update_fields({"title": "X"}, True, p)
    clear_draft(p)
    assert load_draft(p) == EMPTY

def test_broken_file_returns_empty(tmp_path):
    p = tmp_path / "draft.json"
    p.write_text("kein gueltiges json {{{", encoding="utf-8")
    assert load_draft(str(p)) == EMPTY
