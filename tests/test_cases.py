from cases import save_case, list_cases, load_case, delete_case, _name_from_fields

def _draft(title="Faust", author="Goethe", images=1):
    return {
        "fields": {"title": title, "author": author, "book_title": title},
        "images": [{"media_type": "image/jpeg", "data_url": "data:..."}] * images,
        "result_visible": True,
    }

def test_save_und_list(tmp_path):
    d = str(tmp_path / "cases")
    cid = save_case(_draft(), d)
    cases = list_cases(d)
    assert len(cases) == 1
    assert cases[0]["id"] == cid
    assert cases[0]["name"] == "Goethe – Faust"
    assert cases[0]["photo_count"] == 1

def test_load_gibt_entwurf_zurueck(tmp_path):
    d = str(tmp_path / "cases")
    cid = save_case(_draft(title="Werther"), d)
    draft = load_case(cid, d)
    assert draft["fields"]["book_title"] == "Werther"
    assert draft["result_visible"] is True

def test_delete_entfernt_fall(tmp_path):
    d = str(tmp_path / "cases")
    cid = save_case(_draft(), d)
    assert delete_case(cid, d) is True
    assert list_cases(d) == []
    assert load_case(cid, d) is None

def test_liste_neueste_zuerst(tmp_path):
    d = str(tmp_path / "cases")
    c1 = save_case(_draft(title="Eins"), d)
    c2 = save_case(_draft(title="Zwei"), d)
    ids = [c["id"] for c in list_cases(d)]
    assert ids[0] == c2 and ids[1] == c1   # zuletzt gespeicherter oben

def test_name_aus_feldern_oder_fallback(tmp_path):
    assert _name_from_fields({"author": "Kant", "book_title": "Kritik"}) == "Kant – Kritik"
    assert _name_from_fields({}) == ""     # leer -> save_case nutzt dann den Datums-Fallback
    d = str(tmp_path / "cases")
    cid = save_case({"fields": {}, "images": []}, d)
    assert list_cases(d)[0]["name"].startswith("Unbenannter Fall")

def test_kaputte_datei_wird_uebersprungen(tmp_path):
    d = tmp_path / "cases"
    d.mkdir()
    (d / "case_999.json").write_text("kein json {{{", encoding="utf-8")
    save_case(_draft(), str(d))
    assert len(list_cases(str(d))) == 1    # nur der gültige Fall, der kaputte fehlt

def test_unsichere_id_wird_abgewiesen(tmp_path):
    d = str(tmp_path / "cases")
    save_case(_draft(), d)
    assert load_case("../config", d) is None        # kein Ausbruch aus dem Ordner
    assert delete_case("../config", d) is False

def test_load_und_delete_bei_unbekannt(tmp_path):
    d = str(tmp_path / "cases")
    assert load_case("case_123", d) is None
    assert delete_case("case_123", d) is False
    assert list_cases(d) == []             # nicht vorhandener Ordner -> leere Liste
