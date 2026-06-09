from ebay_csv import build_csv, append_listing, COLUMNS

def _parse(data: bytes):
    assert data[:3] == b"\xef\xbb\xbf"            # BOM vorhanden
    text = data.decode("utf-8-sig")
    return text.splitlines()

def test_struktur_bom_und_99_spalten():
    data = build_csv(
        title="Der Hobbit guter Zustand", author="J.R.R. Tolkien",
        book_title="Der Hobbit", language="Deutsch", description="Gut erhalten.",
        price="9.99", condition_id="5000",
        picture_urls=["https://i.ibb.co/abc/1.jpg"],
    )
    lines = _parse(data)
    assert lines[0].startswith("Info;Version=1.0.0;Template=fx_category_template_EBAY_DE")
    header = lines[1].split(";")
    row = lines[2].split(";")
    assert len(header) == 99
    assert len(row) == 99
    assert row[0] == "Add"

def test_felder_an_richtiger_stelle():
    data = build_csv(
        title="T", author="A", book_title="B", language="Deutsch",
        description="D", price="12.50", condition_id="4000",
        picture_urls=["https://x/1.jpg", "https://x/2.jpg"],
    )
    lines = _parse(data)
    header = lines[1].split(";")
    row = dict(zip(header, lines[2].split(";")))
    assert row["*Category"] == "261186"
    assert row["*ConditionID"] == "4000"
    assert row["*C:Autor"] == "A"
    assert row["*StartPrice"] == "12.50"
    assert row["PicURL"] == "https://x/1.jpg|https://x/2.jpg"
    assert row["*ReturnsAcceptedOption"] == "ReturnsNotAccepted"

def test_semikolon_und_titel_werden_bereinigt():
    langer_titel = "X" * 100
    data = build_csv(
        title=langer_titel, author="A", book_title="B", language="Deutsch",
        description="Zeile1; mit Semikolon\nund Umbruch", price="9.99",
        condition_id="5000", picture_urls=["https://x/1.jpg"],
    )
    lines = _parse(data)
    assert len(lines[2].split(";")) == 99
    header = lines[1].split(";")
    row = dict(zip(header, lines[2].split(";")))
    assert ";" not in row["*Description"]
    assert len(row["*Title"]) <= 80

def test_lange_artikelmerkmale_werden_auf_65_gekuerzt():
    langer_titel = ("Fünfftes Supplement zu seinen Historischen und Genealogischen "
                    "wie auch Geographischen Fragen so viel sich im Jahre 1712 zugetragen hat")
    data = build_csv(
        title="T", author="A", book_title=langer_titel, language="Deutsch",
        description="D", price="9.99", condition_id="5000",
        picture_urls=["https://x/1.jpg"], publisher="X" * 80,
    )
    lines = _parse(data)
    header = lines[1].split(";")
    row = dict(zip(header, lines[2].split(";")))
    assert len(row["*C:Buchtitel"]) <= 65
    assert len(row["C:Verlag"]) <= 65
    assert " " not in row["*C:Buchtitel"][-1]   # nicht mitten im Wort abgeschnitten

def test_append_listing_sammelt_in_einer_datei(tmp_path):
    folder = str(tmp_path)
    gemeinsam = dict(author="A", book_title="B", language="Deutsch", description="D",
                     price="9.99", condition_id="5000", picture_urls=["https://x/1.jpg"])
    path, count = append_listing(folder, title="Buch 1", **gemeinsam)
    assert count == 1
    path2, count2 = append_listing(folder, title="Buch 2", **gemeinsam)
    assert path == path2           # gleiche Sammeldatei
    assert count2 == 2
    data = open(path, "rb").read()
    assert data[:3] == b"\xef\xbb\xbf"             # BOM nur einmal am Anfang
    lines = data.decode("utf-8-sig").splitlines()
    assert lines[0].startswith("Info;")
    assert len(lines[1].split(";")) == 99          # genau eine Kopfzeile
    assert lines[2].split(";")[0] == "Add"
    assert lines[3].split(";")[0] == "Add"
    assert len(lines) == 4                          # Info + Kopf + 2 Anzeigen
