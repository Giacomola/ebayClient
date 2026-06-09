from ebay_csv import build_csv, COLUMNS

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
